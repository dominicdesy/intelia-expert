"""
Extension logging.py - ENDPOINTS POUR COMMENTAIRES FEEDBACK
Ajouter ces endpoints à la fin du fichier logging.py existant
"""

# ============================================================================
# NOUVEAUX MODÈLES POUR COMMENTAIRES FEEDBACK
# ============================================================================

class FeedbackCommentUpdate(BaseModel):
    comment: str
    timestamp: Optional[str] = None

class FeedbackWithCommentUpdate(BaseModel):
    feedback: int
    comment: Optional[str] = None
    timestamp: Optional[str] = None

# ============================================================================
# EXTENSION DE LA CLASSE ConversationLogger POUR COMMENTAIRES
# ============================================================================

def extend_conversation_logger():
    """Extension de la classe ConversationLogger avec nouvelles méthodes"""
    
    def update_feedback_comment(self, conversation_id: str, comment: str) -> bool:
        """Met à jour le commentaire feedback d'une conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Vérifier si la colonne feedback_comment existe, sinon la créer
                try:
                    conn.execute("ALTER TABLE conversations ADD COLUMN feedback_comment TEXT")
                    print("✅ Colonne feedback_comment ajoutée à la base")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️ Erreur ajout colonne: {e}")
                
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback_comment = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                """, (comment, conversation_id))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"❌ Erreur mise à jour commentaire feedback: {e}")
            return False
    
    def update_feedback_with_comment(self, conversation_id: str, feedback: int, comment: str = None) -> bool:
        """Met à jour le feedback ET le commentaire d'une conversation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Vérifier si la colonne feedback_comment existe
                try:
                    conn.execute("ALTER TABLE conversations ADD COLUMN feedback_comment TEXT")
                    print("✅ Colonne feedback_comment ajoutée à la base")
                except sqlite3.OperationalError:
                    pass  # Colonne existe déjà
                
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback = ?, feedback_comment = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                """, (feedback, comment, conversation_id))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"❌ Erreur mise à jour feedback avec commentaire: {e}")
            return False
    
    def get_feedback_analytics(self, user_id: str = None, days: int = 7) -> Dict[str, Any]:
        """Génère des analytics détaillées des feedbacks avec commentaires"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Construire la clause WHERE
                where_clause = "WHERE datetime(timestamp) >= datetime('now', '-{} days')".format(days)
                if user_id:
                    where_clause += f" AND user_id = '{user_id}'"
                
                # Statistiques générales
                general_stats = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                        COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                        COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as total_feedback,
                        COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment,
                    AVG(CASE WHEN response_time_ms IS NOT NULL THEN response_time_ms END) as avg_response_time
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
            """.format(days)).fetchone()
            
            # Top commentaires négatifs (pour amélioration)
            negative_comments = conn.execute(f"""
                SELECT question, feedback_comment, timestamp, language
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                AND feedback = -1 
                AND feedback_comment IS NOT NULL 
                AND feedback_comment != ''
                ORDER BY timestamp DESC 
                LIMIT 10
            """.format(days)).fetchall()
            
            # Top commentaires positifs (pour comprendre ce qui marche)
            positive_comments = conn.execute(f"""
                SELECT question, feedback_comment, timestamp, language
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                AND feedback = 1 
                AND feedback_comment IS NOT NULL 
                AND feedback_comment != ''
                ORDER BY timestamp DESC 
                LIMIT 10
            """.format(days)).fetchall()
            
            # Statistiques par langue
            language_stats = conn.execute(f"""
                SELECT 
                    language,
                    COUNT(*) as total,
                    COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive,
                    COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative,
                    COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with_comment
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                GROUP BY language
                ORDER BY total DESC
            """.format(days)).fetchall()
            
            # Utilisateurs les plus actifs avec feedback
            active_users = conn.execute(f"""
                SELECT 
                    user_id,
                    COUNT(*) as total_conversations,
                    COUNT(CASE WHEN feedback IS NOT NULL THEN 1 END) as feedback_given,
                    COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as comments_given
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{} days')
                GROUP BY user_id
                HAVING feedback_given > 0
                ORDER BY comments_given DESC, feedback_given DESC
                LIMIT 10
            """.format(days)).fetchall()
        
        # Calculer les taux
        total_conversations = general_stats[0]
        positive_feedback = general_stats[1]
        negative_feedback = general_stats[2]
        with_comment = general_stats[3]
        total_feedback = positive_feedback + negative_feedback
        
        satisfaction_rate = round(positive_feedback / total_feedback, 3) if total_feedback > 0 else 0
        feedback_rate = round(total_feedback / total_conversations, 3) if total_conversations > 0 else 0
        comment_rate = round(with_comment / total_feedback, 3) if total_feedback > 0 else 0
        
        report = {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_conversations": total_conversations,
                "total_feedback": total_feedback,
                "satisfaction_rate": satisfaction_rate,
                "feedback_rate": feedback_rate,
                "comment_rate": comment_rate,
                "avg_response_time_ms": round(general_stats[4], 2) if general_stats[4] else None
            },
            "feedback_breakdown": {
                "positive": positive_feedback,
                "negative": negative_feedback,
                "with_comment": with_comment
            },
            "language_stats": [
                {
                    "language": lang[0],
                    "total": lang[1],
                    "positive": lang[2],
                    "negative": lang[3],
                    "with_comment": lang[4],
                    "satisfaction_rate": round(lang[2] / (lang[2] + lang[3]), 3) if (lang[2] + lang[3]) > 0 else 0
                } for lang in language_stats
            ],
            "top_negative_feedback": [
                {
                    "question": comment[0][:100] + "..." if len(comment[0]) > 100 else comment[0],
                    "comment": comment[1],
                    "timestamp": comment[2],
                    "language": comment[3]
                } for comment in negative_comments
            ],
            "top_positive_feedback": [
                {
                    "question": comment[0][:100] + "..." if len(comment[0]) > 100 else comment[0],
                    "comment": comment[1],
                    "timestamp": comment[2],
                    "language": comment[3]
                } for comment in positive_comments
            ],
            "most_active_users": [
                {
                    "user_id": user[0][:8] + "..." if len(user[0]) > 12 else user[0],  # Anonymisation partielle
                    "total_conversations": user[1],
                    "feedback_given": user[2],
                    "comments_given": user[3],
                    "engagement_rate": round(user[2] / user[1], 3) if user[1] > 0 else 0
                } for user in active_users
            ]
        }
        
        print(f"✅ [logging] Rapport admin feedback généré")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "report": report,
            "message": f"Rapport feedback pour les {days} derniers jours généré"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur génération rapport admin: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur rapport: {str(e)}")

@router.post("/admin/export-feedback")
async def export_feedback_data(days: int = 30, format: str = "json"):
    """NOUVEAU: Export des données de feedback pour analyse externe"""
    try:
        print(f"📤 [logging] Export données feedback format {format} pour {days} jours")
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute(f"""
                SELECT 
                    conversation_id,
                    user_id,
                    question,
                    feedback,
                    feedback_comment,
                    confidence_score,
                    response_time_ms,
                    language,
                    rag_used,
                    timestamp,
                    updated_at
                FROM conversations 
                WHERE datetime(timestamp) >= datetime('now', '-{days} days')
                AND feedback IS NOT NULL
                ORDER BY timestamp DESC
            """)
            
            data = []
            for row in cursor.fetchall():
                data.append({
                    "conversation_id": row["conversation_id"],
                    "user_id": row["user_id"][:8] + "..." if len(row["user_id"]) > 12 else row["user_id"],  # Anonymisation
                    "question_length": len(row["question"]),
                    "question_preview": row["question"][:50] + "..." if len(row["question"]) > 50 else row["question"],
                    "feedback": "positive" if row["feedback"] == 1 else "negative",
                    "has_comment": bool(row["feedback_comment"]),
                    "comment_length": len(row["feedback_comment"]) if row["feedback_comment"] else 0,
                    "comment_preview": row["feedback_comment"][:100] + "..." if row["feedback_comment"] and len(row["feedback_comment"]) > 100 else row["feedback_comment"],
                    "confidence_score": row["confidence_score"],
                    "response_time_ms": row["response_time_ms"],
                    "language": row["language"],
                    "rag_used": row["rag_used"],
                    "timestamp": row["timestamp"]
                })
        
        print(f"✅ [logging] {len(data)} enregistrements exportés")
        
        if format.lower() == "csv":
            # Pour l'implémentation CSV, on retournerait les headers appropriés
            # et le contenu formaté en CSV
            return {
                "status": "success",
                "message": "Export CSV pas encore implémenté, utiliser JSON",
                "data_preview": data[:5] if data else []
            }
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "export_format": format,
            "period_days": days,
            "total_records": len(data),
            "data": data,
            "message": f"{len(data)} enregistrements feedback exportés"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur export feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur export: {str(e)}")

# ============================================================================
# MISE À JOUR DU SCHÉMA DE BASE DE DONNÉES
# ============================================================================

def update_database_schema():
    """Met à jour le schéma de la base de données pour supporter les commentaires"""
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Ajouter la colonne feedback_comment si elle n'existe pas
            try:
                conn.execute("ALTER TABLE conversations ADD COLUMN feedback_comment TEXT")
                print("✅ Colonne feedback_comment ajoutée à la base de données")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ️ Colonne feedback_comment existe déjà")
                else:
                    print(f"⚠️ Erreur ajout colonne feedback_comment: {e}")
            
            # Créer un index pour les recherches de commentaires
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_comment ON conversations(feedback_comment)")
                print("✅ Index feedback_comment créé")
            except Exception as e:
                print(f"⚠️ Erreur création index: {e}")
            
            # Vérifier le schéma final
            schema_info = conn.execute("PRAGMA table_info(conversations)").fetchall()
            columns = [col[1] for col in schema_info]
            
            print("📋 Colonnes disponibles:", columns)
            
            if "feedback_comment" in columns:
                print("✅ Schema mis à jour avec succès - commentaires feedback supportés")
            else:
                print("❌ Échec mise à jour schema - commentaires feedback non supportés")
                
    except Exception as e:
        print(f"❌ Erreur mise à jour schema: {e}")

# Appliquer la mise à jour du schéma au démarrage
update_database_schema()

# ============================================================================
# TEST ENDPOINT POUR VÉRIFIER LE SUPPORT DES COMMENTAIRES
# ============================================================================

@router.get("/test-comments")
async def test_comment_support():
    """Test du support des commentaires feedback"""
    try:
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Vérifier le schéma
            schema_info = conn.execute("PRAGMA table_info(conversations)").fetchall()
            columns = [col[1] for col in schema_info]
            
            # Compter les commentaires existants
            comment_count = conn.execute("""
                SELECT COUNT(*) FROM conversations 
                WHERE feedback_comment IS NOT NULL AND feedback_comment != ''
            """).fetchone()[0]
            
            # Test d'insertion (rollback)
            conn.execute("BEGIN")
            try:
                test_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO conversations (id, conversation_id, user_id, question, response, feedback, feedback_comment)
                    VALUES (?, ?, 'test_user', 'Test question', 'Test response', 1, 'Test comment')
                """, (str(uuid.uuid4()), test_id))
                
                # Vérifier l'insertion
                result = conn.execute("SELECT feedback_comment FROM conversations WHERE conversation_id = ?", (test_id,)).fetchone()
                test_success = result and result[0] == 'Test comment'
                
                conn.execute("ROLLBACK")  # Annuler le test
                
            except Exception as e:
                conn.execute("ROLLBACK")
                test_success = False
                print(f"❌ Test insertion échoué: {e}")
        
        return {
            "status": "success" if test_success else "error",
            "timestamp": datetime.now().isoformat(),
            "schema_info": {
                "has_feedback_comment_column": "feedback_comment" in columns,
                "total_columns": len(columns),
                "columns": columns
            },
            "comment_stats": {
                "existing_comments": comment_count,
                "insertion_test": "passed" if test_success else "failed"
            },
            "endpoints_available": [
                "/logging/conversation/{id}/comment [PATCH]",
                "/logging/conversation/{id}/feedback-with-comment [PATCH]",
                "/logging/analytics/feedback [GET]",
                "/logging/conversations/with-comments [GET]",
                "/logging/admin/feedback-report [GET]",
                "/logging/admin/export-feedback [POST]"
            ],
            "message": "Support commentaires feedback " + ("opérationnel" if test_success else "non fonctionnel")
        }
        
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Erreur test support commentaires"
        }

print("✅ Extension logging avec commentaires feedback initialisée")
print("🆕 Nouveaux endpoints ajoutés:")
print("   - PATCH /logging/conversation/{id}/comment")
print("   - PATCH /logging/conversation/{id}/feedback-with-comment") 
print("   - GET /logging/analytics/feedback")
print("   - GET /logging/conversations/with-comments")
print("   - GET /logging/admin/feedback-report")
print("   - POST /logging/admin/export-feedback")
print("   - GET /logging/test-comments")_comment
                    FROM conversations 
                    {where_clause}
                """).fetchone()
                
                # Commentaires récents
                recent_comments = conn.execute(f"""
                    SELECT conversation_id, feedback, feedback_comment, timestamp, question
                    FROM conversations 
                    {where_clause}
                    AND feedback_comment IS NOT NULL 
                    AND feedback_comment != ''
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """).fetchall()
                
                # Satisfaction rate
                satisfaction_rate = None
                if general_stats[3] > 0:  # total_feedback
                    satisfaction_rate = round(general_stats[1] / general_stats[3], 3)
                
                return {
                    "period_days": days,
                    "user_id": user_id,
                    "general_stats": {
                        "total_conversations": general_stats[0],
                        "positive_feedback": general_stats[1],
                        "negative_feedback": general_stats[2],
                        "total_feedback": general_stats[3],
                        "with_comment": general_stats[4]
                    },
                    "satisfaction_rate": satisfaction_rate,
                    "comment_rate": round(general_stats[4] / general_stats[3], 3) if general_stats[3] > 0 else 0,
                    "recent_comments": [
                        {
                            "conversation_id": comment[0],
                            "feedback": "positive" if comment[1] == 1 else "negative",
                            "comment": comment[2],
                            "timestamp": comment[3],
                            "question_preview": comment[4][:100] + "..." if len(comment[4]) > 100 else comment[4]
                        } for comment in recent_comments
                    ]
                }
                
        except Exception as e:
            print(f"❌ Erreur analytics feedback: {e}")
            return {
                "error": str(e),
                "period_days": days,
                "user_id": user_id
            }
    
    # Ajouter les méthodes à la classe existante
    ConversationLogger.update_feedback_comment = update_feedback_comment
    ConversationLogger.update_feedback_with_comment = update_feedback_with_comment
    ConversationLogger.get_feedback_analytics = get_feedback_analytics

# Appliquer l'extension
extend_conversation_logger()

# ============================================================================
# NOUVEAUX ENDPOINTS POUR COMMENTAIRES FEEDBACK
# ============================================================================

@router.patch("/conversation/{conversation_id}/comment")
async def update_feedback_comment(conversation_id: str, comment_data: FeedbackCommentUpdate):
    """NOUVEAU: Mettre à jour le commentaire feedback d'une conversation"""
    try:
        print(f"💬 [logging] Réception commentaire pour: {conversation_id}")
        print(f"💬 [logging] Commentaire: {comment_data.comment[:50]}...")
        
        success = logger_instance.update_feedback_comment(conversation_id, comment_data.comment)
        
        if success:
            print(f"✅ [logging] Commentaire mis à jour: {conversation_id}")
            return {
                "status": "success",
                "message": "Commentaire feedback mis à jour avec succès", 
                "conversation_id": conversation_id,
                "comment": comment_data.comment[:100] + "..." if len(comment_data.comment) > 100 else comment_data.comment,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ [logging] Conversation non trouvée pour commentaire: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [logging] Erreur commentaire feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur commentaire: {str(e)}")

@router.patch("/conversation/{conversation_id}/feedback-with-comment")
async def update_feedback_with_comment(conversation_id: str, feedback_data: FeedbackWithCommentUpdate):
    """NOUVEAU: Mettre à jour le feedback ET le commentaire d'une conversation"""
    try:
        print(f"📊💬 [logging] Réception feedback avec commentaire pour: {conversation_id}")
        print(f"📊💬 [logging] Feedback: {feedback_data.feedback}")
        print(f"💬 [logging] Commentaire: {feedback_data.comment[:50] + '...' if feedback_data.comment else 'Aucun'}")
        
        success = logger_instance.update_feedback_with_comment(
            conversation_id, 
            feedback_data.feedback,
            feedback_data.comment
        )
        
        if success:
            print(f"✅ [logging] Feedback avec commentaire mis à jour: {conversation_id}")
            return {
                "status": "success",
                "message": "Feedback avec commentaire mis à jour avec succès", 
                "conversation_id": conversation_id,
                "feedback": feedback_data.feedback,
                "comment": feedback_data.comment[:100] + "..." if feedback_data.comment and len(feedback_data.comment) > 100 else feedback_data.comment,
                "timestamp": datetime.now().isoformat()
            }
        else:
            print(f"❌ [logging] Conversation non trouvée pour feedback avec commentaire: {conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation non trouvée")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [logging] Erreur feedback avec commentaire: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur feedback avec commentaire: {str(e)}")

@router.get("/analytics/feedback")
async def get_feedback_analytics(user_id: str = None, days: int = 7):
    """NOUVEAU: Analytics détaillées des feedbacks avec commentaires"""
    try:
        print(f"📊 [logging] Récupération analytics feedback pour: {user_id or 'tous les utilisateurs'}")
        print(f"📊 [logging] Période: {days} jours")
        
        analytics = logger_instance.get_feedback_analytics(user_id, days)
        
        print(f"✅ [logging] Analytics feedback récupérées")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "analytics": analytics,
            "message": f"Analytics feedback pour les {days} derniers jours"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur analytics feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur analytics: {str(e)}")

@router.get("/conversations/with-comments")
async def get_conversations_with_comments(limit: int = 20, user_id: str = None):
    """NOUVEAU: Récupérer les conversations avec commentaires feedback"""
    try:
        print(f"💬 [logging] Récupération conversations avec commentaires")
        print(f"💬 [logging] Limite: {limit}, User: {user_id or 'tous'}")
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            where_clause = "WHERE feedback_comment IS NOT NULL AND feedback_comment != ''"
            params = []
            
            if user_id:
                where_clause += " AND user_id = ?"
                params.append(user_id)
            
            cursor = conn.execute(f"""
                SELECT conversation_id, user_id, question, feedback, feedback_comment, timestamp, language
                FROM conversations 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT ?
            """, params + [limit])
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    "conversation_id": row["conversation_id"],
                    "user_id": row["user_id"],
                    "question": row["question"],
                    "feedback": "positive" if row["feedback"] == 1 else "negative",
                    "feedback_comment": row["feedback_comment"],
                    "timestamp": row["timestamp"],
                    "language": row["language"]
                })
        
        print(f"✅ [logging] {len(conversations)} conversations avec commentaires récupérées")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "conversations": conversations,
            "count": len(conversations),
            "message": f"{len(conversations)} conversations avec commentaires trouvées"
        }
        
    except Exception as e:
        print(f"❌ [logging] Erreur récupération conversations avec commentaires: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur récupération: {str(e)}")

@router.get("/admin/feedback-report")
async def get_admin_feedback_report(days: int = 30):
    """NOUVEAU: Rapport administrateur des feedbacks avec commentaires"""
    try:
        print(f"📋 [logging] Génération rapport admin feedback pour {days} jours")
        
        with sqlite3.connect(logger_instance.db_path) as conn:
            # Statistiques générales
            general_stats = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_conversations,
                    COUNT(CASE WHEN feedback = 1 THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN feedback = -1 THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN feedback_comment IS NOT NULL AND feedback_comment != '' THEN 1 END) as with