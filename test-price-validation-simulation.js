// Simulation of the price validation logic
function simulatePriceValidation(projectData) {
  const budget = projectData.budget || {};
  const bidStats = projectData.bid_stats || {};
  const aiEstimatedPrice = 1200; // Example AI estimate
  
  console.log(`\n🧮 Simulating Price Validation for Project ${projectData.id}`);
  console.log(`💰 Budget: $${budget.minimum || 0} - $${budget.maximum || 'N/A'}`);
  console.log(`📊 Average Bid: $${bidStats.bid_avg || 'N/A'}`);
  console.log(`🤖 AI Estimated Price: $${aiEstimatedPrice}`);
  
  // Step 1: Minimum price validation
  let minimumBidAmount = budget.minimum || 100;
  let bidAmount = aiEstimatedPrice;
  
  console.log(`\n📋 Step 1: Minimum Price Check`);
  if (bidAmount < minimumBidAmount) {
    bidAmount = minimumBidAmount;
    console.log(`   ⬆️ Adjusted to minimum: $${bidAmount}`);
  } else {
    console.log(`   ✅ Above minimum ($${minimumBidAmount}): $${bidAmount}`);
  }
  
  // Step 2: Maximum price validation (NEW!)
  console.log(`\n📋 Step 2: Maximum Price Check (NEW!)`);
  let maximumAllowedBid = null;
  let referencePrice = null;
  let referencePriceType = null;
  
  // Try maximum budget first
  if (budget.maximum && budget.maximum > 0) {
    referencePrice = budget.maximum;
    referencePriceType = 'maximum budget';
  } else if (bidStats.bid_avg && bidStats.bid_avg > 0) {
    referencePrice = bidStats.bid_avg;
    referencePriceType = 'average bid';
  }
  
  if (referencePrice && referencePrice > 0) {
    maximumAllowedBid = Math.ceil(referencePrice * 1.8); // 80% above
    console.log(`   🎯 Reference: ${referencePriceType} = $${referencePrice}`);
    console.log(`   🚫 Maximum allowed (180%): $${maximumAllowedBid}`);
    
    if (bidAmount > maximumAllowedBid) {
      console.log(`   ⬇️ ADJUSTMENT NEEDED: $${bidAmount} → $${maximumAllowedBid}`);
      bidAmount = maximumAllowedBid;
    } else {
      console.log(`   ✅ Within limit: $${bidAmount} ≤ $${maximumAllowedBid}`);
    }
  } else {
    console.log(`   ⚠️ No reference price available - no maximum limit applied`);
  }
  
  console.log(`\n🎯 Final Result:`);
  console.log(`   Original AI Estimate: $${aiEstimatedPrice}`);
  console.log(`   Final Bid Amount: $${bidAmount}`);
  console.log(`   Adjustment: ${aiEstimatedPrice !== bidAmount ? 'YES' : 'NO'}`);
  
  return bidAmount;
}

// Test with actual project data
const testProjects = [
  {
    id: 32796265,
    budget: { minimum: 10, maximum: 40 },
    bid_stats: { bid_avg: 56.72 }
  },
  {
    id: 38531034,
    budget: { minimum: 10, maximum: 30 },
    bid_stats: { bid_avg: 39.67 }
  },
  {
    id: 39463845,
    budget: { minimum: 500, maximum: 1000 },
    bid_stats: { bid_avg: 954.23 }
  }
];

console.log('🧪 Testing Enhanced Price Validation Simulation\n');
console.log('This shows how the price validation SHOULD work...\n');

testProjects.forEach(project => {
  simulatePriceValidation(project);
  console.log('\n' + '='.repeat(60));
});

console.log('\n📝 Summary:');
console.log('• Project 1 ($10-$40): AI estimate $1200 should be capped at $72 (180% of $40)');
console.log('• Project 2 ($10-$30): AI estimate $1200 should be capped at $54 (180% of $30)'); 
console.log('• Project 3 ($500-$1000): AI estimate $1200 is within $1800 limit ✅');
console.log('\nIf the actual API is not doing this, there might be a bug in the implementation!'); 