// types/supabase.ts - Types de base Supabase pour Intelia Expert

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string;
          email: string;
          name: string;
          avatar_url?: string;
          user_type: "producer" | "professional";
          language: string;
          created_at: string;
          updated_at: string;
          consent_given: boolean;
          consent_date?: string;
        };
        Insert: {
          id?: string;
          email: string;
          name: string;
          avatar_url?: string;
          user_type?: "producer" | "professional";
          language?: string;
          created_at?: string;
          updated_at?: string;
          consent_given?: boolean;
          consent_date?: string;
        };
        Update: {
          id?: string;
          email?: string;
          name?: string;
          avatar_url?: string;
          user_type?: "producer" | "professional";
          language?: string;
          created_at?: string;
          updated_at?: string;
          consent_given?: boolean;
          consent_date?: string;
        };
      };
      conversations: {
        Row: {
          id: string;
          user_id: string;
          title?: string;
          messages: any[]; // JSON array
          created_at: string;
          updated_at: string;
          language: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          title?: string;
          messages?: any[];
          created_at?: string;
          updated_at?: string;
          language?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          title?: string;
          messages?: any[];
          created_at?: string;
          updated_at?: string;
          language?: string;
        };
      };
      feedback: {
        Row: {
          id: string;
          user_id: string;
          message_id: string;
          rating: "positive" | "negative";
          comment?: string;
          category?: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          message_id: string;
          rating: "positive" | "negative";
          comment?: string;
          category?: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          message_id?: string;
          rating?: "positive" | "negative";
          comment?: string;
          category?: string;
          created_at?: string;
        };
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      user_type: "producer" | "professional";
      language_code: "fr" | "en" | "es" | "pt" | "de" | "nl" | "pl";
      feedback_rating: "positive" | "negative";
    };
  };
}

// Types utilitaires
export type Tables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Row"];
export type InsertTables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Insert"];
export type UpdateTables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Update"];

// Types spécifiques
export type UserRow = Tables<"users">;
export type ConversationRow = Tables<"conversations">;
export type FeedbackRow = Tables<"feedback">;

export type UserInsert = InsertTables<"users">;
export type ConversationInsert = InsertTables<"conversations">;
export type FeedbackInsert = InsertTables<"feedback">;

export type UserUpdate = UpdateTables<"users">;
export type ConversationUpdate = UpdateTables<"conversations">;
export type FeedbackUpdate = UpdateTables<"feedback">;

// Types d'énumération
export type UserType = Database["public"]["Enums"]["user_type"];
export type LanguageCode = Database["public"]["Enums"]["language_code"];
export type FeedbackRating = Database["public"]["Enums"]["feedback_rating"];
