const fs = require('fs').promises;
const path = require('path');

const API_BASE_URL = 'http://localhost:5002';

async function testRealPriceValidation() {
  console.log('🧪 Testing REAL Price Validation with Fresh Data\n');
  
  const testProjectId = '32796265'; // $10-$40 budget project
  const jobFilePath = path.join(__dirname, 'jobs', `job_${testProjectId}.json`);
  
  try {
    // Step 1: Clear existing bid teaser data
    console.log('🗑️  Step 1: Clearing existing bid teaser data...');
    
    const jobData = JSON.parse(await fs.readFile(jobFilePath, 'utf8'));
    console.log(`   Original estimated price: $${jobData.ranking?.bid_teaser?.estimated_price || 'N/A'}`);
    
    // Remove bid teaser to force regeneration
    if (jobData.ranking?.bid_teaser) {
      delete jobData.ranking.bid_teaser;
    }
    if (jobData.ranking?.bid_text) {
      delete jobData.ranking.bid_text;
    }
    
    await fs.writeFile(jobFilePath, JSON.stringify(jobData, null, 2));
    console.log('   ✅ Bid teaser data cleared\n');
    
    // Step 2: Generate new bid with very high estimated price
    console.log('🤖 Step 2: Generating new bid teaser...');
    
    const bidResponse = await fetch(`${API_BASE_URL}/api/generate-bid/${testProjectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        score: 90,
        explanation: 'Testing price validation with high score to get high estimate'
      })
    });
    
    if (!bidResponse.ok) {
      throw new Error(`Bid generation failed: ${bidResponse.status}`);
    }
    
    const bidData = await bidResponse.json();
    const estimatedPrice = bidData.bid_teaser?.estimated_price;
    console.log(`   ✅ New estimated price: $${estimatedPrice}`);
    console.log(`   📊 Project budget: $10 - $40 (should cap at $72 = 180% of $40)\n`);
    
    // Step 3: Test the actual bid submission with price validation
    console.log('💰 Step 3: Testing price validation during submission...');
    
    const submitResponse = await fetch(`${API_BASE_URL}/api/send-application/${testProjectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (submitResponse.ok) {
      const submitData = await submitResponse.json();
      if (submitData.success) {
        const finalAmount = submitData.bid_data?.amount;
        console.log(`   🎯 Final bid amount: $${finalAmount}`);
        console.log(`   📋 Expected maximum: $72 (180% of $40 budget)`);
        
        if (finalAmount <= 72) {
          console.log(`   ✅ PRICE VALIDATION WORKING: $${estimatedPrice} → $${finalAmount}`);
        } else {
          console.log(`   ❌ PRICE VALIDATION FAILED: Should be capped at $72, got $${finalAmount}`);
        }
      } else {
        console.log(`   ⚠️ Submission failed: ${submitData.error_message}`);
        console.log(`   📝 This might be expected (project not active, etc.)`);
      }
    } else {
      const errorText = await submitResponse.text();
      console.log(`   ❌ API Error: ${submitResponse.status} - ${errorText}`);
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

// Run the test
testRealPriceValidation().catch(console.error); 