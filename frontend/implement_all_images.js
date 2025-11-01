/**
 * Complete script to implement image display in frontend
 * Modifies: types/index.ts, apiService.ts, and page.tsx
 */
const fs = require('fs');
const path = require('path');

console.log('🖼️ Implementing complete image display in frontend...\n');

let successCount = 0;
let skipCount = 0;

// ============================================================================
// 1. UPDATE types/index.ts - Add images to EndEvent
// ============================================================================
const typesPath = 'C:/Software_Development/intelia-cognito/frontend/types/index.ts';
let typesContent = fs.readFileSync(typesPath, 'utf8');

const endEventOld = `export type EndEvent = {
  type: "end";
  total_time?: number;
  confidence?: number;
  documents_used?: number;
  source?: string;
};`;

const endEventNew = `export type EndEvent = {
  type: "end";
  total_time?: number;
  confidence?: number;
  documents_used?: number;
  source?: string;
  images?: Array<{
    image_id: string;
    image_url: string;
    caption?: string;
    image_type?: string;
  }>;
};`;

if (typesContent.includes(endEventOld)) {
  typesContent = typesContent.replace(endEventOld, endEventNew);
  fs.writeFileSync(typesPath, typesContent, 'utf8');
  console.log('✅ 1/6: Updated types/index.ts - EndEvent with images');
  successCount++;
} else if (typesContent.includes('images?: Array<{')) {
  console.log('⏭️  1/6: types/index.ts EndEvent already has images');
  skipCount++;
} else {
  console.log('⚠️  1/6: types/index.ts pattern not found - may need manual update');
}

// ============================================================================
// 2. UPDATE apiService.ts - Add images to EnhancedAIResponse interface
// ============================================================================
const apiServicePath = 'C:/Software_Development/intelia-cognito/frontend/app/chat/services/apiService.ts';
let apiServiceContent = fs.readFileSync(apiServicePath, 'utf8');

const interfaceOld = `interface EnhancedAIResponse {
  response: string;
  conversation_id: string;
  agentMetadata: AgentMetadata;
}`;

const interfaceNew = `interface EnhancedAIResponse {
  response: string;
  conversation_id: string;
  agentMetadata: AgentMetadata;
  images?: Array<{
    image_id: string;
    image_url: string;
    caption?: string;
    image_type?: string;
  }>;
}`;

if (apiServiceContent.includes(interfaceOld)) {
  apiServiceContent = apiServiceContent.replace(interfaceOld, interfaceNew);
  fs.writeFileSync(apiServicePath, apiServiceContent, 'utf8');
  console.log('✅ 2/6: Updated apiService.ts - EnhancedAIResponse interface');
  successCount++;
} else if (apiServiceContent.match(/interface EnhancedAIResponse[\s\S]{0,200}images\?:/)) {
  console.log('⏭️  2/6: apiService.ts interface already has images');
  skipCount++;
} else {
  console.log('⚠️  2/6: apiService.ts interface pattern not found - may need manual update');
}

// ============================================================================
// 3. UPDATE apiService.ts - Capture images from END event
// ============================================================================
apiServiceContent = fs.readFileSync(apiServicePath, 'utf8');

const endEventHandlerOld = `              // 🆕 CAPTURER LA SOURCE RÉELLE (PostgreSQL/Weaviate/External LLM)
              if (endEvent.source) {
                agentMetadata.response_source = endEvent.source;
                secureLog.log(\`[apiService] Source capturée: \${endEvent.source}\`);
              }
              break;`;

const endEventHandlerNew = `              // 🆕 CAPTURER LA SOURCE RÉELLE (PostgreSQL/Weaviate/External LLM)
              if (endEvent.source) {
                agentMetadata.response_source = endEvent.source;
                secureLog.log(\`[apiService] Source capturée: \${endEvent.source}\`);
              }
              // 🖼️ CAPTURER LES IMAGES
              if (endEvent.images && Array.isArray(endEvent.images)) {
                (agentMetadata as any).images = endEvent.images;
                secureLog.log(\`[apiService] 🖼️ \${endEvent.images.length} images retrieved\`);
              }
              break;`;

if (apiServiceContent.includes(endEventHandlerOld) && !apiServiceContent.includes('// 🖼️ CAPTURER LES IMAGES')) {
  apiServiceContent = apiServiceContent.replace(endEventHandlerOld, endEventHandlerNew);
  fs.writeFileSync(apiServicePath, apiServiceContent, 'utf8');
  console.log('✅ 3/6: Updated apiService.ts - END event handler captures images');
  successCount++;
} else if (apiServiceContent.includes('// 🖼️ CAPTURER LES IMAGES')) {
  console.log('⏭️  3/6: apiService.ts already captures images in END event');
  skipCount++;
} else {
  console.log('⚠️  3/6: apiService.ts END event pattern not found - may need manual update');
}

// ============================================================================
// 4. UPDATE apiService.ts - Include images in response
// ============================================================================
apiServiceContent = fs.readFileSync(apiServicePath, 'utf8');

const responseOld = `    // Construction de la réponse dans le format attendu par l'interface
    const processedResponse: EnhancedAIResponse = {
      response: finalResponse,
      conversation_id: finalConversationId,
      agentMetadata,
    };

    return processedResponse;`;

const responseNew = `    // Construction de la réponse dans le format attendu par l'interface
    const processedResponse: EnhancedAIResponse = {
      response: finalResponse,
      conversation_id: finalConversationId,
      agentMetadata,
      // 🖼️ Include images from agent metadata if available
      images: (agentMetadata as any).images || [],
    };

    return processedResponse;`;

if (apiServiceContent.includes(responseOld)) {
  apiServiceContent = apiServiceContent.replace(responseOld, responseNew);
  fs.writeFileSync(apiServicePath, apiServiceContent, 'utf8');
  console.log('✅ 4/6: Updated apiService.ts - Response includes images');
  successCount++;
} else if (apiServiceContent.match(/const processedResponse: EnhancedAIResponse[\s\S]{0,300}images:/)) {
  console.log('⏭️  4/6: apiService.ts response already includes images');
  skipCount++;
} else {
  console.log('⚠️  4/6: apiService.ts response pattern not found - may need manual update');
}

// ============================================================================
// 5. UPDATE page.tsx - Add imageUrls to bot message creation
// ============================================================================
const pagePath = 'C:/Software_Development/intelia-cognito/frontend/app/chat/page.tsx';
let pageContent = fs.readFileSync(pagePath, 'utf8');

// Find the bot message creation pattern - we need to be careful here
const botMessagePattern = /const botMessage: Message = \{[\s\S]*?id: botMessageId,[\s\S]*?content: aiResponse\.response,[\s\S]*?isUser: false,/;

if (botMessagePattern.test(pageContent) && !pageContent.includes('imageUrls: aiResponse.images')) {
  // We need to find the exact location and insert imageUrls
  const match = pageContent.match(/const botMessage: Message = \{[\s\S]{0,500}\};/);

  if (match) {
    const oldBotMessage = match[0];
    // Insert imageUrls before the closing brace
    const newBotMessage = oldBotMessage.replace(
      /(\s+)(\};)$/,
      `$1// 🖼️ Add images from API response\n$1imageUrls: aiResponse.images?.map(img => img.image_url) || [],$1$2`
    );

    pageContent = pageContent.replace(oldBotMessage, newBotMessage);
    fs.writeFileSync(pagePath, pageContent, 'utf8');
    console.log('✅ 5/6: Updated page.tsx - Bot message includes imageUrls');
    successCount++;
  } else {
    console.log('⚠️  5/6: page.tsx bot message pattern not precise enough');
  }
} else if (pageContent.includes('imageUrls: aiResponse.images')) {
  console.log('⏭️  5/6: page.tsx already includes imageUrls in bot message');
  skipCount++;
} else {
  console.log('⚠️  5/6: page.tsx bot message pattern not found - may need manual update');
}

// ============================================================================
// 6. VERIFY page.tsx has image rendering code
// ============================================================================
pageContent = fs.readFileSync(pagePath, 'utf8');

if (pageContent.includes('message.imageUrls') && pageContent.includes('Image.map')) {
  console.log('✅ 6/6: page.tsx already has image rendering code');
  successCount++;
} else {
  console.log('⚠️  6/6: page.tsx may be missing image rendering code');
  console.log('      Check lines 380-401 for image rendering');
}

// ============================================================================
// SUMMARY
// ============================================================================
console.log('\n' + '='.repeat(60));
console.log('📊 SUMMARY:');
console.log('  ✅ Successfully updated: ' + successCount + ' items');
console.log('  ⏭️  Already updated: ' + skipCount + ' items');
console.log('  Total: ' + (successCount + skipCount) + '/6');
console.log('='.repeat(60));

if (successCount > 0) {
  console.log('\n✅ Frontend image implementation complete!');
  console.log('\n📝 Next steps:');
  console.log('  1. Rebuild frontend: npm run build');
  console.log('  2. Deploy to production');
  console.log('  3. Test with Nano queries');
}
