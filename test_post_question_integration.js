const fetch = require('node-fetch');

async function testPostQuestionIntegration() {
  console.log('🧪 Testing Post Question Integration...\n');
  
  const API_BASE = 'http://localhost:5002';
  
  // Test project ID (use a real project ID from your jobs)
  const testProjectId = '39540325'; // Replace with actual project ID
  
  console.log(`📋 Testing question posting for project ${testProjectId}...\n`);
  
  try {
    console.log('📝 Calling post-question API endpoint...');
    
    const response = await fetch(`${API_BASE}/api/post-question/${testProjectId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        projectId: testProjectId
      })
    });
    
    console.log(`📡 API Response Status: ${response.status}`);
    
    if (response.ok) {
      const result = await response.json();
      console.log('✅ Post Question API Success!');
      console.log('📤 Response Data:', {
        success: result.success,
        message: result.message,
        projectId: result.projectId
      });
      
      if (result.output) {
        console.log('\n📋 Python Script Output:');
        console.log(result.output);
      }
      
    } else {
      const errorData = await response.json();
      console.log('❌ Post Question API Error:');
      console.log('📥 Error Data:', errorData);
    }
    
  } catch (error) {
    console.log('❌ Network/Connection Error:', error.message);
  }
  
  console.log('\n🏁 Test completed!');
  console.log('\n💡 Next steps:');
  console.log('   1. Enable "Post Question" in Vue frontend');
  console.log('   2. Enable "Automatic Bidding"');
  console.log('   3. Check auto-bidding logs for question posting');
}

// Run the test
testPostQuestionIntegration().catch(console.error); 