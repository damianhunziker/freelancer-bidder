#!/usr/bin/env node

/**
 * Test script to verify the new client-side automatic bidding approach
 * This simulates the frontend flow: generate bid text → automatically submit bid
 */

const API_BASE = 'http://localhost:5002';

async function testClientSideAutoBidding() {
  console.log('🧪 Testing Client-Side Automatic Bidding');
  console.log('=========================================\n');
  
  try {
    // Step 1: Get available projects
    console.log('📋 Step 1: Getting available projects...');
    const projectsResponse = await fetch(`${API_BASE}/api/jobs`);
    
    if (!projectsResponse.ok) {
      throw new Error(`Failed to get projects: ${projectsResponse.status}`);
    }
    
    const projects = await projectsResponse.json();
    console.log(`   ✅ Found ${projects.length} projects\n`);
    
    // Find a project to test with
    const testProject = projects.find(p => 
      p.project_details?.id && 
      p.ranking?.score > 40 // Only test on decent scoring projects
    );
    
    if (!testProject) {
      console.log('   ⚠️  No suitable test project found');
      return;
    }
    
    const projectId = testProject.project_details.id;
    const projectTitle = testProject.project_details.title?.substring(0, 50) + '...';
    
    console.log(`   🎯 Selected test project: ${projectId}`);
    console.log(`   📝 Title: ${projectTitle}`);
    console.log(`   ⭐ Score: ${testProject.ranking?.score || 'N/A'}`);
    console.log(`   🤖 Has bid text: ${testProject.ranking?.bid_teaser?.first_paragraph ? 'Yes' : 'No'}\n`);
    
    // Step 2: Generate bid text if needed (simulating frontend flow)
    if (!testProject.ranking?.bid_teaser?.first_paragraph) {
      console.log('🤖 Step 2: Generating bid text...');
      
      const bidResponse = await fetch(`${API_BASE}/api/generate-bid/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          score: testProject.ranking?.score || 75,
          explanation: testProject.ranking?.explanation || 'Test client-side automatic bidding'
        })
      });
      
      if (!bidResponse.ok) {
        const errorText = await bidResponse.text();
        throw new Error(`Bid generation failed: ${bidResponse.status} - ${errorText}`);
      }
      
      const bidData = await bidResponse.json();
      
      if (bidData.success) {
        console.log('   ✅ Bid text generated successfully!');
        console.log(`   💰 Estimated price: $${bidData.bid_teaser?.estimated_price || 'N/A'}`);
        console.log(`   ⏱️  Estimated days: ${bidData.bid_teaser?.estimated_days || 'N/A'}`);
        
        // Update our test project with the generated bid text
        testProject.ranking.bid_teaser = bidData.bid_teaser;
      } else {
        throw new Error(`Bid generation failed: ${bidData.error}`);
      }
    } else {
      console.log('📄 Step 2: Using existing bid text...');
    }
    
    // Step 3: Automatically submit the bid (simulating frontend callback)
    console.log('\n📤 Step 3: Automatically submitting bid (client-side approach)...');
    
    const submitResponse = await fetch(`${API_BASE}/api/send-application/${projectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!submitResponse.ok) {
      const errorText = await submitResponse.text();
      throw new Error(`Bid submission failed: ${submitResponse.status} - ${errorText}`);
    }
    
    const submitData = await submitResponse.json();
    
    if (submitData.success) {
      console.log('   ✅ Bid submitted successfully!');
      console.log(`   💰 Amount: $${submitData.bid_data?.amount || 'N/A'}`);
      console.log(`   📅 Period: ${submitData.bid_data?.period || 'N/A'} days`);
      console.log(`   🔗 Project URL: ${submitData.project_url}`);
    } else {
      console.log('   ⚠️  Bid submission failed (but text was generated)');
      console.log(`   📋 Error: ${submitData.error_message || 'Unknown error'}`);
      console.log('   💡 This would trigger manual submission in the frontend');
    }
    
    console.log('\n🎉 Client-Side Auto-Bidding Test Completed!');
    console.log('=============================================');
    console.log('✅ New approach: Generate text → Client-side submission');
    console.log('✅ Better error handling and user feedback');
    console.log('✅ Cleaner separation of concerns');
    console.log('✅ Frontend has full control over the bidding flow\n');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.log('\nPlease check:');
    console.log('- API server is running on port 5002');
    console.log('- Freelancer API credentials are configured');
    console.log('- Projects are available in jobs directory');
  }
}

// Run the test
testClientSideAutoBidding(); 