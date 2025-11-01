# Frontend Images Implementation Guide

## Modifications Required

### 1. Update apiService.ts to capture images from END event

**File**: `frontend/app/chat/services/apiService.ts`

**Location**: Line ~432 in the `end` event handler

**Current Code**:
```typescript
case "end":
  const endEvent = event as EndEvent;
  secureLog.log("[apiService] Stream terminé (end event):", endEvent);
  // Extraire les métadonnées de fin si disponibles
  if (endEvent.documents_used !== undefined) {
    agentMetadata.sources_used = endEvent.documents_used;
  }
  if (endEvent.confidence !== undefined) {
    // Stocker la confidence finale pour référence
    (agentMetadata as any).final_confidence = endEvent.confidence;
  }
  // 🆕 CAPTURER LA SOURCE RÉELLE (PostgreSQL/Weaviate/External LLM)
  if (endEvent.source) {
    agentMetadata.response_source = endEvent.source;
    secureLog.log(`[apiService] Source capturée: ${endEvent.source}`);
  }
  break;
```

**Modified Code** (add after line ~447):
```typescript
case "end":
  const endEvent = event as EndEvent;
  secureLog.log("[apiService] Stream terminé (end event):", endEvent);
  // Extraire les métadonnées de fin si disponibles
  if (endEvent.documents_used !== undefined) {
    agentMetadata.sources_used = endEvent.documents_used;
  }
  if (endEvent.confidence !== undefined) {
    // Stocker la confidence finale pour référence
    (agentMetadata as any).final_confidence = endEvent.confidence;
  }
  // 🆕 CAPTURER LA SOURCE RÉELLE (PostgreSQL/Weaviate/External LLM)
  if (endEvent.source) {
    agentMetadata.response_source = endEvent.source;
    secureLog.log(`[apiService] Source capturée: ${endEvent.source}`);
  }
  // 🖼️ CAPTURER LES IMAGES
  if (endEvent.images && Array.isArray(endEvent.images)) {
    (agentMetadata as any).images = endEvent.images;
    secureLog.log(`[apiService] 🖼️ ${endEvent.images.length} images retrieved`);
  }
  break;
```

### 2. Update EndEvent type to include images

**File**: `frontend/types/index.ts`

**Find the EndEvent interface** (around line 154):
```typescript
export interface EndEvent {
  type: "end";
  total_time: number;
  confidence: number;
  documents_used: number;
  source: string;
  // ...other fields
}
```

**Add images field**:
```typescript
export interface EndEvent {
  type: "end";
  total_time: number;
  confidence: number;
  documents_used: number;
  source: string;
  images?: Array<{
    image_id: string;
    image_url: string;
    caption?: string;
    image_type?: string;
    source_file?: string;
    width?: number;
    height?: number;
    format?: string;
  }>;
  // ...other fields
}
```

### 3. Return images from generateAIResponse

**File**: `frontend/app/chat/services/apiService.ts`

**Location**: Around line 703 in the `generateAIResponse` function

**Current Code**:
```typescript
// Construction de la réponse dans le format attendu par l'interface
const processedResponse: EnhancedAIResponse = {
  response: finalResponse,
  conversation_id: finalConversationId,
  agentMetadata,
};

return processedResponse;
```

**Modified Code**:
```typescript
// Construction de la réponse dans le format attendu par l'interface
const processedResponse: EnhancedAIResponse = {
  response: finalResponse,
  conversation_id: finalConversationId,
  agentMetadata,
  // 🖼️ Include images from agent metadata if available
  images: (agentMetadata as any).images || [],
};

return processedResponse;
```

### 4. Update EnhancedAIResponse type

**File**: `frontend/app/chat/services/apiService.ts`

**Find EnhancedAIResponse interface** (around line 151):
```typescript
interface EnhancedAIResponse {
  response: string;
  conversation_id: string;
  agentMetadata: AgentMetadata;
}
```

**Modified**:
```typescript
interface EnhancedAIResponse {
  response: string;
  conversation_id: string;
  agentMetadata: AgentMetadata;
  images?: Array<{
    image_id: string;
    image_url: string;
    caption?: string;
    image_type?: string;
  }>;
}
```

### 5. Update page.tsx to use images from API response

**File**: `frontend/app/chat/page.tsx`

**Location**: In the `handleSendMessage` function, after receiving the AI response

**Find where the bot message is created** (around line 1200-1250):
```typescript
const botMessage: Message = {
  id: botMessageId,
  content: aiResponse.response,
  isUser: false,
  timestamp: new Date(),
  conversation_id: aiResponse.conversation_id,
  agent_metadata: aiResponse.agentMetadata,
  // ...other fields
};
```

**Modified**:
```typescript
const botMessage: Message = {
  id: botMessageId,
  content: aiResponse.response,
  isUser: false,
  timestamp: new Date(),
  conversation_id: aiResponse.conversation_id,
  agent_metadata: aiResponse.agentMetadata,
  // 🖼️ Add images from API response
  imageUrls: aiResponse.images?.map(img => img.image_url) || [],
  // ...other fields
};
```

### 6. Render images in message display

**File**: `frontend/app/chat/page.tsx`

**Location**: In the message rendering section (around line 1600-1700)

**Find where bot messages are rendered**:
```tsx
{!msg.isUser && (
  <div className="bot-message">
    <TypewriterMessage
      key={msg.id}
      content={msg.content}
      // ... other props
    />
  </div>
)}
```

**Modified** (add after the TypewriterMessage):
```tsx
{!msg.isUser && (
  <div className="bot-message">
    <TypewriterMessage
      key={msg.id}
      content={msg.content}
      // ... other props
    />

    {/* 🖼️ Display images if present */}
    {msg.imageUrls && msg.imageUrls.length > 0 && (
      <div className="message-images" style={{
        marginTop: '12px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '12px'
      }}>
        {msg.imageUrls.map((imageUrl, idx) => (
          <div key={idx} style={{
            borderRadius: '8px',
            overflow: 'hidden',
            border: '1px solid #e0e0e0'
          }}>
            <img
              src={imageUrl}
              alt={`Image ${idx + 1}`}
              style={{
                width: '100%',
                height: 'auto',
                display: 'block'
              }}
              onError={(e) => {
                console.error(`Failed to load image: ${imageUrl}`);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        ))}
      </div>
    )}
  </div>
)}
```

## Summary of Changes

1. **apiService.ts**: Capture images from END event and include in response
2. **types/index.ts**: Add images field to EndEvent interface
3. **page.tsx**: Add imageUrls to bot Message and render images

## Testing

After implementing these changes:
1. Deploy to Digital Ocean
2. Ask a question about Nano system
3. Verify images appear in the response
4. Check browser console for any errors

## Expected Result

When asking about Nano installation, the response should include 3 diagrams from the Nano manual, displayed below the text response in a grid layout.
