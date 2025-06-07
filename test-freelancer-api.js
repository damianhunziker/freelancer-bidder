const fetch = require('node-fetch');
const config = require('./vue-frontend/config-loader');

// Use project ID from command line or default
const TEST_PROJECT_ID = process.argv[2] || 39486083;

console.log('🧪 Testing Freelancer API Authentication...\n');

// Test 1: Check if we can authenticate and get user info
async function testAuthentication() {
  console.log('📋 Test 1: Authentication Check');
  console.log('API Key:', config.FREELANCER_API_KEY ? `${config.FREELANCER_API_KEY.substring(0, 10)}...` : 'NOT SET');
  console.log('User ID:', config.FREELANCER_USER_ID);
  
  try {
    const response = await fetch('https://www.freelancer.com/api/users/0.1/users/self', {
      method: 'GET',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Response Status:', response.status);
    console.log('Response Headers:', Object.fromEntries(response.headers));
    
    const data = await response.text();
    console.log('Response Body:', data);
    
    if (response.ok) {
      const userData = JSON.parse(data);
      console.log('✅ Authentication successful!');
      console.log('User Info:', {
        id: userData.result?.id,
        username: userData.result?.username,
        display_name: userData.result?.display_name
      });
      return userData.result;
    } else {
      console.log('❌ Authentication failed!');
      return null;
    }
  } catch (error) {
    console.log('❌ Authentication error:', error.message);
    return null;
  }
}

// Test 2: Try to get user info by username
async function testUserByUsername() {
  console.log('\n📋 Test 2: Get User by Username');
  
  try {
    const response = await fetch(`https://www.freelancer.com/api/users/0.1/users?usernames[]=${config.FREELANCER_USER_ID}`, {
      method: 'GET',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Response Status:', response.status);
    const data = await response.text();
    console.log('Response Body:', data);
    
    if (response.ok) {
      const userData = JSON.parse(data);
      const user = userData.result?.users?.[config.FREELANCER_USER_ID];
      if (user) {
        console.log('✅ User found!');
        console.log('User Info:', {
          id: user.id,
          username: user.username,
          display_name: user.display_name
        });
        return user.id;
      } else {
        console.log('❌ User not found in response');
        return null;
      }
    } else {
      console.log('❌ Failed to get user info');
      return null;
    }
  } catch (error) {
    console.log('❌ Error getting user info:', error.message);
    return null;
  }
}

// Test 3: Get project info
async function testProjectInfo() {
  console.log('\n📋 Test 3: Get Project Info');
  
  try {
    const response = await fetch(`https://www.freelancer.com/api/projects/0.1/projects/${TEST_PROJECT_ID}`, {
      method: 'GET',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Response Status:', response.status);
    const data = await response.text();
    console.log('Response Body (first 500 chars):', data.substring(0, 500));
    
    if (response.ok) {
      const projectData = JSON.parse(data);
      console.log('✅ Project info retrieved!');
      console.log('Project Info:', {
        id: projectData.result?.id,
        title: projectData.result?.title,
        owner_id: projectData.result?.owner_id,
        currency: projectData.result?.currency
      });
      return projectData.result;
    } else {
      console.log('❌ Failed to get project info');
      return null;
    }
  } catch (error) {
    console.log('❌ Error getting project info:', error.message);
    return null;
  }
}

// Test 4: Try to submit a test bid
async function testBidSubmission(userInfo, projectInfo) {
  console.log('\n📋 Test 4: Test Bid Submission');
  
  if (!userInfo || !projectInfo) {
    console.log('❌ Skipping bid test - missing user or project info');
    return;
  }
  
  const bidData = {
    project_id: parseInt(TEST_PROJECT_ID),
    bidder_id: userInfo.id, // Use the actual numeric user ID
    amount: 100,
    period: 7,
    milestone_percentage: 100,
    description: "Test bid from API - please ignore"
  };
  
  console.log('Bid Data:', bidData);
  
  try {
    const response = await fetch('https://www.freelancer.com/api/projects/0.1/bids/', {
      method: 'POST',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(bidData)
    });
    
    console.log('Response Status:', response.status);
    console.log('Response Headers:', Object.fromEntries(response.headers));
    
    const data = await response.text();
    console.log('Response Body:', data);
    
    if (response.ok) {
      console.log('✅ Bid submitted successfully!');
      const bidResult = JSON.parse(data);
      console.log('Bid Result:', bidResult.result);
    } else {
      console.log('❌ Bid submission failed');
      try {
        const errorData = JSON.parse(data);
        console.log('Error Details:', errorData);
      } catch (e) {
        console.log('Raw Error:', data);
      }
    }
  } catch (error) {
    console.log('❌ Bid submission error:', error.message);
  }
}

// Test 5: Check OAuth token scopes
async function testTokenScopes() {
  console.log('\n📋 Test 5: Check OAuth Token Scopes');
  
  try {
    const response = await fetch('https://www.freelancer.com/api/users/0.1/users/self/oauth_scopes/', {
      method: 'GET',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Response Status:', response.status);
    const data = await response.text();
    console.log('Response Body:', data);
    
    if (response.ok) {
      const scopeData = JSON.parse(data);
      console.log('✅ Token scopes retrieved!');
      console.log('Available Scopes:', scopeData.result);
      
      const requiredScopes = ['basic', 'fln:project_manage'];
      const hasRequiredScopes = requiredScopes.every(scope => 
        scopeData.result?.some(s => s.name === scope)
      );
      
      if (hasRequiredScopes) {
        console.log('✅ All required scopes are available');
      } else {
        console.log('❌ Missing required scopes. Need: basic, fln:project_manage');
      }
    } else {
      console.log('❌ Failed to get token scopes');
    }
  } catch (error) {
    console.log('❌ Error checking token scopes:', error.message);
  }
}

// Run all tests
async function runAllTests() {
  console.log('🚀 Starting Freelancer API Tests\n');
  
  // Test authentication first
  const userInfo = await testAuthentication();
  
  // Get user by username to get numeric ID
  const numericUserId = await testUserByUsername();
  
  // Update user info with numeric ID if found
  if (numericUserId && userInfo) {
    userInfo.id = numericUserId;
  }
  
  // Get project info
  const projectInfo = await testProjectInfo();
  
  // Check token scopes
  await testTokenScopes();
  
  // Only test bid submission if everything else works
  if (userInfo && projectInfo) {
    console.log('\n⚠️  About to test bid submission. This will create a real bid!');
    console.log('Waiting 5 seconds... Press Ctrl+C to cancel if needed');
    
    await new Promise(resolve => setTimeout(resolve, 5000));
    await testBidSubmission(userInfo, projectInfo);
  }
  
  console.log('\n🏁 Tests completed!');
}

// Handle command line arguments
if (process.argv.includes('--no-bid')) {
  console.log('⚠️  Skipping bid submission test (--no-bid flag)');
  runAllTests().then(() => {
    console.log('\n🏁 Tests completed (without bid submission)!');
  });
} else {
  runAllTests();
} 