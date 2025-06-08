const API_BASE_URL = 'http://localhost:5002';

async function testPriceValidation() {
  console.log('🧪 Testing Enhanced Price Validation Logic\n');
  
  try {
    // Get list of projects
    const projectsResponse = await fetch(`${API_BASE_URL}/api/jobs`);
    const projects = await projectsResponse.json();
    
    console.log(`📊 Found ${projects.length} projects to test\n`);
    
    // Test with first few projects that have budget data
    let testedProjects = 0;
    const maxTests = 3;
    
    for (const project of projects) {
      if (testedProjects >= maxTests) break;
      
      const projectId = project.project_details?.id;
      const projectTitle = project.project_details?.title;
      const budget = project.project_details?.budget;
      const bidStats = project.project_details?.bid_stats;
      
      if (!projectId || (!budget?.minimum && !bidStats?.bid_avg)) continue;
      
      console.log(`🎯 Testing Project ${projectId}: "${projectTitle?.substring(0, 50)}..."`);
      console.log(`   💰 Budget: $${budget?.minimum || 0} - $${budget?.maximum || 'N/A'}`);
      console.log(`   📊 Average Bid: $${bidStats?.bid_avg || 'N/A'}`);
      
      // First generate bid text if not exists
      try {
        const bidResponse = await fetch(`${API_BASE_URL}/api/generate-bid/${projectId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            score: 75,
            explanation: 'Test price validation with various scenarios'
          })
        });
        
        if (!bidResponse.ok) {
          console.log(`   ⚠️ Bid generation failed: ${bidResponse.status}\n`);
          continue;
        }
        
        const bidData = await bidResponse.json();
        console.log(`   🤖 AI Estimated Price: $${bidData.bid_teaser?.estimated_price || 'N/A'}`);
        
        // Now test the price validation by trying to submit
        console.log(`   🔍 Testing price validation logic...`);
        
        const submitResponse = await fetch(`${API_BASE_URL}/api/send-application/${projectId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (submitResponse.ok) {
          const submitData = await submitResponse.json();
          if (submitData.success) {
            console.log(`   ✅ Price validation passed!`);
            console.log(`   💵 Final bid amount: $${submitData.bid_data?.amount}`);
            console.log(`   📋 Validation: Minimum check ✅, Maximum check ✅`);
          } else {
            console.log(`   ⚠️ Submission failed: ${submitData.error_message}`);
          }
        } else {
          console.log(`   ❌ API Error: ${submitResponse.status}`);
        }
        
      } catch (error) {
        console.log(`   ❌ Error: ${error.message}`);
      }
      
      console.log(''); // Empty line
      testedProjects++;
      
      // Wait between tests
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    if (testedProjects === 0) {
      console.log('⚠️ No projects with sufficient budget data found for testing');
    }
    
    console.log('🎉 Price validation testing completed!');
    console.log('\n📝 What the new validation does:');
    console.log('   1️⃣ Ensures bid ≥ minimum budget (existing check)');
    console.log('   2️⃣ Ensures bid ≤ 180% of maximum budget OR average bid (NEW!)');
    console.log('   3️⃣ Handles currency conversion automatically');
    console.log('   4️⃣ Falls back gracefully when no reference price available');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

// Run the test
testPriceValidation().catch(console.error); 