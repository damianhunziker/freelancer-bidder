const fetch = require('node-fetch');
const config = require('./vue-frontend/config-loader');

console.log('🔍 Debugging Freelancer OAuth Token...\n');

async function testTokenValidity() {
  console.log('📋 Testing OAuth Token Validity');
  console.log('Token (partial):', config.FREELANCER_API_KEY ? config.FREELANCER_API_KEY.substring(0, 15) + '...' : 'NOT SET');
  console.log('User ID:', config.FREELANCER_USER_ID);
  
  if (!config.FREELANCER_API_KEY || config.FREELANCER_API_KEY === 'your_freelancer_oauth_token_here') {
    console.log('❌ Token not properly configured in config.py');
    return null;
  }
  
  // Test different authentication methods
  const testEndpoints = [
    {
      name: 'Self User Info',
      url: 'https://www.freelancer.com/api/users/0.1/users/self',
      method: 'GET'
    },
    {
      name: 'Self User Info (with compact)',
      url: 'https://www.freelancer.com/api/users/0.1/users/self?compact=true',
      method: 'GET'
    },
    {
      name: 'User by Username',
      url: `https://www.freelancer.com/api/users/0.1/users?usernames[]=${config.FREELANCER_USER_ID}`,
      method: 'GET'
    }
  ];
  
  for (const endpoint of testEndpoints) {
    console.log(`\n🧪 Testing: ${endpoint.name}`);
    console.log(`URL: ${endpoint.url}`);
    
    try {
      const response = await fetch(endpoint.url, {
        method: endpoint.method,
        headers: {
          'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
          'Content-Type': 'application/json',
          'User-Agent': 'FreelancerBidder/1.0'
        }
      });
      
      console.log(`Status: ${response.status} ${response.statusText}`);
      console.log('Response Headers:', Object.fromEntries(response.headers));
      
      const data = await response.text();
      console.log('Response (first 300 chars):', data.substring(0, 300));
      
      if (response.ok) {
        try {
          const jsonData = JSON.parse(data);
          console.log('✅ Success!');
          
          if (endpoint.name === 'Self User Info' && jsonData.result) {
            console.log('🎯 User Details:');
            console.log('- ID:', jsonData.result.id);
            console.log('- Username:', jsonData.result.username);
            console.log('- Display Name:', jsonData.result.display_name);
            console.log('- Role:', jsonData.result.role);
            console.log('- Chosen Role:', jsonData.result.chosen_role);
            console.log('- Account Status:', jsonData.result.status);
          }
          
          if (endpoint.name === 'User by Username' && jsonData.result?.users) {
            const users = jsonData.result.users;
            console.log('🎯 Found Users:', Object.keys(users));
            
            // The user object is keyed by user ID, not username
            const userEntries = Object.entries(users);
            if (userEntries.length > 0) {
              const [userId, userData] = userEntries[0];
              console.log('- User ID:', userId);
              console.log('- Username:', userData.username);
              console.log('- Display Name:', userData.display_name);
            }
          }
        } catch (parseError) {
          console.log('⚠️ Valid response but failed to parse JSON:', parseError.message);
        }
      } else {
        console.log('❌ Failed');
        try {
          const errorData = JSON.parse(data);
          console.log('Error Details:', errorData);
        } catch (e) {
          console.log('Raw Error:', data);
        }
      }
    } catch (error) {
      console.log('❌ Request failed:', error.message);
    }
  }
}

async function testTokenFormat() {
  console.log('\n🔍 Analyzing Token Format...');
  
  const token = config.FREELANCER_API_KEY;
  if (!token) {
    console.log('❌ No token found in configuration');
    return;
  }
  
  console.log('Token Length:', token.length);
  console.log('Token Start:', token.substring(0, 10));
  console.log('Token End:', token.substring(-10));
  console.log('Contains Spaces:', token.includes(' '));
  console.log('Contains Special Chars:', /[^a-zA-Z0-9]/.test(token));
  
  // Check if it looks like a valid OAuth token format
  if (token.length < 20) {
    console.log('⚠️ Token seems too short for OAuth token');
  } else if (token.length > 200) {
    console.log('⚠️ Token seems too long for OAuth token');
  } else {
    console.log('✅ Token length seems reasonable');
  }
}

async function testAlternativeHeaders() {
  console.log('\n🧪 Testing Alternative Header Formats...');
  
  const testHeaders = [
    {
      name: 'Standard Format',
      headers: {
        'Freelancer-OAuth-V1': config.FREELANCER_API_KEY,
        'Content-Type': 'application/json'
      }
    },
    {
      name: 'Bearer Format',
      headers: {
        'Authorization': `Bearer ${config.FREELANCER_API_KEY}`,
        'Content-Type': 'application/json'
      }
    },
    {
      name: 'OAuth Format',
      headers: {
        'Authorization': `OAuth ${config.FREELANCER_API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  ];
  
  for (const test of testHeaders) {
    console.log(`\n🔬 Testing: ${test.name}`);
    
    try {
      const response = await fetch('https://www.freelancer.com/api/users/0.1/users/self?compact=true', {
        method: 'GET',
        headers: test.headers
      });
      
      console.log(`Status: ${response.status}`);
      
      if (response.status === 200) {
        console.log('✅ This header format works!');
        const data = await response.json();
        console.log('User ID:', data.result?.id);
        console.log('Username:', data.result?.username);
        return test.headers;
      } else {
        const errorText = await response.text();
        console.log('❌ Failed:', errorText.substring(0, 100));
      }
    } catch (error) {
      console.log('❌ Request error:', error.message);
    }
  }
  
  return null;
}

async function runDebugTests() {
  console.log('🚀 Starting OAuth Debug Tests\n');
  
  await testTokenFormat();
  await testTokenValidity();
  const workingHeaders = await testAlternativeHeaders();
  
  if (workingHeaders) {
    console.log('\n🎉 Found working authentication method!');
    console.log('Working Headers:', workingHeaders);
  } else {
    console.log('\n❌ No working authentication method found');
    console.log('\n💡 Possible Issues:');
    console.log('1. Token is expired or invalid');
    console.log('2. Token doesn\'t have required scopes');
    console.log('3. Token format is incorrect');
    console.log('4. Account may be suspended or restricted');
    console.log('\n🔧 Next Steps:');
    console.log('1. Generate a new OAuth token at https://developers.freelancer.com/');
    console.log('2. Ensure token has "basic" and "fln:project_manage" scopes');
    console.log('3. Verify account is in good standing');
  }
  
  console.log('\n🏁 Debug tests completed!');
}

runDebugTests(); 