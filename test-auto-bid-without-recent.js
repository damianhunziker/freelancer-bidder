const fetch = require('node-fetch');

async function testAutoBiddingWithoutRecent() {
  console.log('🧪 Testing Automatic Bidding WITHOUT Recent Filter...\n');
  
  const API_BASE = 'http://localhost:5002';
  
  // Test projects that qualify for auto-bidding (from our analysis)
  const qualifyingProjects = [
    { id: '39479804', title: 'Dolibarr ERP Custom Module Developer' },
    { id: '39479923', title: 'Secure Cybersecurity Website Development' },
    { id: '39481180', title: 'Custom Saudi School Management Module for Odoo' },
    { id: '39481929', title: 'Chatbot con rag y parada de flujo...' }
  ];
  
  console.log(`🎯 Testing ${qualifyingProjects.length} qualifying projects...\n`);
  
  for (const project of qualifyingProjects) {
    console.log(`📋 Testing project ${project.id}: "${project.title}"`);
    
    try {
      // Step 1: Generate bid text (if not exists)
      console.log(`   📝 Generating bid text...`);
      const bidResponse = await fetch(`${API_BASE}/api/generate-bid/${project.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          score: 75,
          explanation: 'Test automatic bid generation'
        })
      });
      
      if (bidResponse.ok) {
        const bidData = await bidResponse.json();
        console.log(`   ✅ Bid text generated successfully`);
        console.log(`   💰 Estimated price: $${bidData.bid_teaser?.estimated_price}`);
        console.log(`   ⏱️  Estimated days: ${bidData.bid_teaser?.estimated_days}`);
      } else {
        console.log(`   ⚠️  Bid generation failed: ${bidResponse.status}`);
        continue;
      }
      
      // Step 2: Submit bid
      console.log(`   📤 Submitting bid...`);
      const submitResponse = await fetch(`${API_BASE}/api/send-application/${project.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (submitResponse.ok) {
        const submitData = await submitResponse.json();
        if (submitData.success) {
          console.log(`   ✅ Bid submitted successfully!`);
          console.log(`   💰 Amount: $${submitData.bid_data?.amount}`);
          console.log(`   📅 Period: ${submitData.bid_data?.period} days`);
        } else {
          console.log(`   ⚠️  Bid submission failed: ${submitData.error_message}`);
        }
      } else {
        console.log(`   ❌ Bid submission error: ${submitResponse.status}`);
      }
      
    } catch (error) {
      console.log(`   ❌ Error: ${error.message}`);
    }
    
    console.log(''); // Empty line between projects
    
    // Wait between projects
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('🏁 Test completed!');
}

testAutoBiddingWithoutRecent().catch(console.error); 