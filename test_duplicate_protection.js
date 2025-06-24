const fetch = require('node-fetch');

async function testDuplicateProtection() {
  console.log('🧪 Testing Duplicate Protection System...\n');
  
  const API_BASE = 'http://localhost:5002';
  
  // Test project ID (use a real project ID)
  const testProjectId = '39540325';
  
  console.log(`📋 Testing duplicate protection for project ${testProjectId}...\n`);
  
  // Test 1: Simulate multiple simultaneous bid generations
  console.log('🔄 Test 1: Multiple simultaneous bid generations...');
  
  const bidPromises = [];
  for (let i = 0; i < 3; i++) {
    console.log(`   Starting bid generation ${i + 1}/3...`);
    const promise = fetch(`${API_BASE}/api/generate-bid/${testProjectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        score: 75,
        explanation: `Test duplicate protection ${i + 1}`
      })
    }).then(res => res.json()).then(data => {
      console.log(`   ✅ Bid generation ${i + 1} completed: ${data.success ? 'SUCCESS' : 'FAILED'}`);
      return { index: i + 1, data };
    }).catch(error => {
      console.log(`   ❌ Bid generation ${i + 1} error: ${error.message}`);
      return { index: i + 1, error: error.message };
    });
    
    bidPromises.push(promise);
    
    // Small delay between requests
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  // Wait for all requests to complete
  const bidResults = await Promise.all(bidPromises);
  
  console.log('\n📊 Bid Generation Results:');
  bidResults.forEach(result => {
    if (result.data) {
      console.log(`   ${result.index}: ${result.data.success ? '✅ SUCCESS' : '❌ FAILED'} - ${result.data.message || result.data.error_message || 'No message'}`);
    } else {
      console.log(`   ${result.index}: ❌ ERROR - ${result.error}`);
    }
  });
  
  // Test 2: Simulate multiple simultaneous question postings
  console.log('\n🔄 Test 2: Multiple simultaneous question postings...');
  
  const questionPromises = [];
  for (let i = 0; i < 3; i++) {
    console.log(`   Starting question posting ${i + 1}/3...`);
    const promise = fetch(`${API_BASE}/api/post-question/${testProjectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        projectId: testProjectId
      })
    }).then(res => res.json()).then(data => {
      console.log(`   ✅ Question posting ${i + 1} completed: ${data.success ? 'SUCCESS' : 'FAILED'}`);
      return { index: i + 1, data };
    }).catch(error => {
      console.log(`   ❌ Question posting ${i + 1} error: ${error.message}`);
      return { index: i + 1, error: error.message };
    });
    
    questionPromises.push(promise);
    
    // Small delay between requests
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  // Wait for all requests to complete
  const questionResults = await Promise.all(questionPromises);
  
  console.log('\n📊 Question Posting Results:');
  questionResults.forEach(result => {
    if (result.data) {
      console.log(`   ${result.index}: ${result.data.success ? '✅ SUCCESS' : '❌ FAILED'} - ${result.data.message || result.data.error || 'No message'}`);
    } else {
      console.log(`   ${result.index}: ❌ ERROR - ${result.error}`);
    }
  });
  
  console.log('\n🏁 Duplicate Protection Test completed!');
  console.log('\n💡 Expected behavior:');
  console.log('   - Only ONE bid generation should succeed');
  console.log('   - Only ONE question posting should succeed');
  console.log('   - Other attempts should be blocked with duplicate protection messages');
  console.log('\n🔍 Check the Vue frontend Auto-Bid Debug Console for detailed logs');
}

// Run the test
testDuplicateProtection().catch(console.error); 