/**
 * Shared utility function for formatting bid text
 * Used by both frontend (ProjectList.vue) and backend (server/index.js)
 */

function formatBidText(bidTeaser) {
  if (!bidTeaser) return '';
  
  // Priority 1: Use final_composed_text if available (new composition format)
  if (bidTeaser.final_composed_text) {
    console.log('[Debug] Using final_composed_text for bid formatting');
    return bidTeaser.final_composed_text.trim();
  }
  
  // Priority 2: Fallback to traditional paragraph-based formatting
  console.log('[Debug] Using traditional paragraph-based formatting');
  
  // Format the bid text with proper line breaks and spacing
  let formattedText = '';

  if (bidTeaser.greeting) {
    formattedText += bidTeaser.greeting + '\n\n';
  }
  
  if (bidTeaser.first_paragraph) {
    formattedText += bidTeaser.first_paragraph + '\n\n';
  }

  if (bidTeaser.second_paragraph) {
    formattedText += bidTeaser.second_paragraph + '\n\n';
  }

  if (bidTeaser.third_paragraph) {
    formattedText += bidTeaser.third_paragraph + '\n\n';
  }

  if (bidTeaser.fourth_paragraph) {
    formattedText += bidTeaser.fourth_paragraph + '\n\n';
  }

  if (bidTeaser.closing) {
    formattedText += bidTeaser.closing + '\n';
  }

  formattedText += 'Damian Hunziker';

  // Replace — with ...
  formattedText = formattedText.replace(/—/g, '... ');
  
  return formattedText.trim();
}

// Export for both CommonJS (Node.js) and ES6 modules (Vue.js)
if (typeof module !== 'undefined' && module.exports) {
  // Node.js/CommonJS export
  module.exports = { formatBidText };
} else if (typeof window !== 'undefined') {
  // Browser environment - ES6 module export (will be handled by build system)
  window.formatBidTextUtils = { formatBidText };
}

// ES6 module export for Vue.js build system
export { formatBidText }; 