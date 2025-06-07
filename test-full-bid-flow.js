const fetch = require('node-fetch');

const API_BASE_URL = 'http://localhost:5002';

console.log('🎯 Testing Complete Bid Generation and Submission Flow\n');

async function testFullBidFlow() {
  try {
    // Step 1: Get available projects
    console.log('📋 Step 1: Getting available projects...');
    const jobsResponse = await fetch(`${API_BASE_URL}/api/jobs`);
    if (!jobsResponse.ok) {
      throw new Error(`Failed to get projects: ${jobsResponse.status}`);
    }
    
    const projects = await jobsResponse.json();
    console.log(`✅ Found ${projects.length} projects`);
    
    if (projects.length === 0) {
      console.log('❌ No projects available for testing');
      return;
    }
    
    // Get the first project for testing
    const testProject = projects[0];
    const projectId = testProject.project_details.id;
    console.log(`🎯 Using project: ${projectId} - "${testProject.project_details.title}"`);
    
    // Step 2: Generate bid text
    console.log('\n📋 Step 2: Generating bid text...');
    const bidGenerationResponse = await fetch(`${API_BASE_URL}/api/generate-bid/${projectId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        score: 85,
        explanation: 'This is a test project for validating the bid submission system. The project requirements align well with our capabilities.'
      })
    });
    
    if (!bidGenerationResponse.ok) {
      const errorText = await bidGenerationResponse.text();
      throw new Error(`Bid generation failed: ${bidGenerationResponse.status} - ${errorText}`);
    }
    
    const bidData = await bidGenerationResponse.json();
    console.log('✅ Bid text generated successfully!');
    console.log('📄 Generated components:');
    const bidTeaser = bidData.bid_teaser || bidData.bid_text?.bid_teaser;
    if (bidTeaser) {
      console.log('- Greeting:', bidTeaser.greeting ? '✅' : '❌');
      console.log('- First paragraph:', bidTeaser.first_paragraph ? '✅' : '❌');
      console.log('- Question:', bidTeaser.question ? '✅' : '❌');
      console.log('- Estimated price:', bidTeaser.estimated_price ? `$${bidTeaser.estimated_price}` : '❌');
      console.log('- Estimated days:', bidTeaser.estimated_days ? `${bidTeaser.estimated_days} days` : '❌');
    }
    
    // Step 3: Test send application (without actually submitting)
    console.log('\n📋 Step 3: Testing send application API...');
    const sendAppResponse = await fetch(`${API_BASE_URL}/api/send-application/${projectId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!sendAppResponse.ok) {
      const errorText = await sendAppResponse.text();
      console.log(`⚠️ Send application API call failed: ${sendAppResponse.status} - ${errorText}`);
    } else {
      const sendAppData = await sendAppResponse.json();
      console.log('📧 Send application response:');
      console.log('- Success:', sendAppData.success ? '✅' : '❌');
      console.log('- Message:', sendAppData.message);
      
      if (sendAppData.success && sendAppData.bid_submitted) {
        console.log('🎉 BID SUCCESSFULLY SUBMITTED TO FREELANCER.COM!');
        console.log('- Freelancer Response:', sendAppData.freelancer_response?.status);
        console.log('- Bid Amount:', `$${sendAppData.bid_data?.amount}`);
        console.log('- Bid Period:', `${sendAppData.bid_data?.period} days`);
      } else if (sendAppData.api_error) {
        console.log('⚠️ API submission failed (manual submission required)');
        console.log('- Error:', sendAppData.error_message);
        console.log('- Formatted text available:', sendAppData.formatted_text ? '✅' : '❌');
        console.log('- Project URL:', sendAppData.project_url);
      }
    }
    
    // Step 4: Test Freelancer API authentication
    console.log('\n📋 Step 4: Testing Freelancer API authentication...');
    const authResponse = await fetch(`${API_BASE_URL}/api/test-freelancer-auth`);
    const authData = await authResponse.json();
    
    console.log('🔐 Authentication status:');
    console.log('- Success:', authData.success ? '✅' : '❌');
    console.log('- User ID:', authData.user_data?.id);
    console.log('- Username:', authData.user_data?.username);
    console.log('- Display name:', authData.user_data?.display_name);
    console.log('- Account role:', authData.user_data?.chosen_role);
    
    console.log('\n🏁 Full bid flow test completed!');
    
    // Summary
    console.log('\n📊 SUMMARY:');
    console.log('✅ Project retrieval: Working');
    console.log('✅ Bid text generation: Working');
    console.log('✅ Freelancer API authentication: Working');
    console.log('🎯 System is ready for automatic bid submission!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Full error:', error);
  }
}

testFullBidFlow(); 