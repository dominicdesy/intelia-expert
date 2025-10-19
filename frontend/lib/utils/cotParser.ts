/**
 * cotParser.ts - Chain-of-Thought XML Parser
 *
 * Parse structured CoT responses with <thinking>, <analysis>, and <answer> tags
 */

export interface CotSections {
  thinking?: string;
  analysis?: string;
  answer: string; // Always present (fallback to full content)
  hasStructure: boolean; // True if XML tags were found
}

/**
 * Parse CoT XML structure from LLM response
 *
 * @param content - Raw LLM response (may contain XML tags)
 * @returns Parsed sections
 */
export function parseCotResponse(content: string): CotSections {
  if (!content || !content.trim()) {
    return {
      answer: '',
      hasStructure: false
    };
  }

  const trimmedContent = content.trim();

  // Check if content has XML structure
  const hasThinking = /<thinking>/i.test(trimmedContent);
  const hasAnalysis = /<analysis>/i.test(trimmedContent);
  const hasAnswer = /<answer>/i.test(trimmedContent);

  // If no structure, return entire content as answer
  if (!hasThinking && !hasAnalysis && !hasAnswer) {
    return {
      answer: trimmedContent,
      hasStructure: false
    };
  }

  // Extract sections using regex
  const result: CotSections = {
    answer: '',
    hasStructure: true
  };

  // Extract <thinking> section
  const thinkingMatch = trimmedContent.match(/<thinking>([\s\S]*?)<\/thinking>/i);
  if (thinkingMatch) {
    result.thinking = thinkingMatch[1].trim();
  }

  // Extract <analysis> section
  const analysisMatch = trimmedContent.match(/<analysis>([\s\S]*?)<\/analysis>/i);
  if (analysisMatch) {
    result.analysis = analysisMatch[1].trim();
  }

  // Extract <answer> section
  const answerMatch = trimmedContent.match(/<answer>([\s\S]*?)<\/answer>/i);
  if (answerMatch) {
    result.answer = answerMatch[1].trim();
  } else {
    // Fallback: Use content after last closing tag
    const lastTagMatch = trimmedContent.match(/<\/(?:thinking|analysis|answer)>\s*([\s\S]*)$/i);
    if (lastTagMatch && lastTagMatch[1].trim()) {
      result.answer = lastTagMatch[1].trim();
    } else {
      // Last fallback: Use entire content
      result.answer = trimmedContent;
    }
  }

  return result;
}

/**
 * Remove XML tags from content (for display or debugging)
 *
 * @param content - Content with potential XML tags
 * @returns Clean content without XML tags
 */
export function stripCotTags(content: string): string {
  return content
    .replace(/<thinking>[\s\S]*?<\/thinking>/gi, '')
    .replace(/<analysis>[\s\S]*?<\/analysis>/gi, '')
    .replace(/<answer>|<\/answer>/gi, '')
    .trim();
}

/**
 * Check if content contains CoT structure
 *
 * @param content - Content to check
 * @returns True if contains any CoT XML tags
 */
export function hasCotStructure(content: string): boolean {
  return /<(?:thinking|analysis|answer)>/i.test(content);
}
