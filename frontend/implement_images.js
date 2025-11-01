/**
 * Script to implement image display in frontend
 */
const fs = require('fs');

console.log('🖼️ Implementing image display in frontend...\n');

// 1. Update apiService.ts - Add images to END event handler
const apiServicePath = 'C:/Software_Development/intelia-cognito/frontend/app/chat/services/apiService.ts';
let apiServiceContent = fs.readFileSync(apiServicePath, 'utf8');

const endEventOld = `              // 🆕 CAPTURER LA SOURCE RÉELLE (PostgreSQL/Weaviate/External LLM)
              if (endEvent.source) {
                agentMetadata.response_source = endEvent.source;
                secureLog.log(\`[apiService] Source capturée: \${endEvent.source}\`);
              }
              break;`;

const endEventNew = `              // 🆕 CAPTURER LA SOURCE RÉELLE (PostgreSQL/Weaviate/External LLM)
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

if (apiServiceContent.includes(endEventOld) && !apiServiceContent.includes('// 🖼️ CAPTURER LES IMAGES')) {
  apiServiceContent = apiServiceContent.replace(endEventOld, endEventNew);
  fs.writeFileSync(apiServicePath, apiServiceContent, 'utf8');
  console.log('✅ 1/4: Updated apiService.ts - END event handler');
} else {
  console.log('⏭️  1/4: apiService.ts END event already updated or code changed');
}

// 2. Update apiService.ts - Add images to EnhancedAIResponse return
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

apiServiceContent = fs.readFileSync(apiServicePath, 'utf8');
if (apiServiceContent.includes(responseOld)) {
  apiServiceContent = apiServiceContent.replace(responseOld, responseNew);
  fs.writeFileSync(apiServicePath, apiServiceContent, 'utf8');
  console.log('✅ 2/4: Updated apiService.ts - EnhancedAIResponse return');
} else {
  console.log('⏭️  2/4: apiService.ts response already updated or code changed');
}

// 3. Update apiService.ts - Add images to interface
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

apiServiceContent = fs.readFileSync(apiServicePath, 'utf8');
if (apiServiceContent.includes(interfaceOld)) {
  apiServiceContent = apiServiceContent.replace(interfaceOld, interfaceNew);
  fs.writeFileSync(apiServicePath, apiServiceContent, 'utf8');
  console.log('✅ 3/4: Updated apiService.ts - EnhancedAIResponse interface');
} else {
  console.log('⏭️  3/4: EnhancedAIResponse interface already updated or code changed');
}

console.log('\n✅ Frontend API service updated!');
console.log('\n📝 Next steps:');
console.log('  1. Update types/index.ts to add images to EndEvent interface');
console.log('  2. Update page.tsx to:');
console.log('     - Add imageUrls to bot Message');
console.log('     - Render images in message display');
console.log('\nSee FRONTEND_IMAGES_IMPLEMENTATION.md for detailed instructions.');
