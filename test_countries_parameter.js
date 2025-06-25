const fs = require('fs');
const path = require('path');

// Load configuration
const configPath = path.join(__dirname, 'config.py');
let FREELANCER_API_KEY = '';

try {
  const configContent = fs.readFileSync(configPath, 'utf8');
  const apiKeyMatch = configContent.match(/FREELANCER_API_KEY\s*=\s*['"]([^'"]+)['"]/);
  if (apiKeyMatch) {
    FREELANCER_API_KEY = apiKeyMatch[1];
  } else {
    console.error('❌ FREELANCER_API_KEY not found in config.py');
    process.exit(1);
  }
} catch (error) {
  console.error('❌ Error reading config.py:', error.message);
  process.exit(1);
}

const BASE_URL = 'https://www.freelancer.com/api/projects/0.1/projects/active/';

/**
 * Test the countries[] parameter with different country combinations
 */
async function testCountriesParameter() {
  console.log('🌍 Testing countries[] parameter for Freelancer Active Projects API\n');

  const testCases = [
    {
      name: 'No countries filter',
      countries: null,
      description: 'Baseline test without country filtering'
    },
    {
      name: 'Single country: Australia',
      countries: ['au'],
      description: 'Test filtering for Australian projects only'
    },
    {
      name: 'Single country: United States',
      countries: ['us'],
      description: 'Test filtering for US projects only'
    },
    {
      name: 'Single country: Germany',
      countries: ['de'],
      description: 'Test filtering for German projects only'
    },
    {
      name: 'Single country: United Kingdom',
      countries: ['gb'],
      description: 'Test filtering for UK projects only'
    },
    {
      name: 'Multiple countries: English-speaking',
      countries: ['au', 'us', 'gb', 'ca'],
      description: 'Test filtering for English-speaking countries'
    },
    {
      name: 'Multiple countries: DACH region',
      countries: ['de', 'at', 'ch'],
      description: 'Test filtering for German-speaking countries'
    },
    {
      name: 'Multiple countries: Europe',
      countries: ['de', 'fr', 'it', 'es', 'nl', 'gb'],
      description: 'Test filtering for major European countries'
    },
    {
      name: 'Invalid country code',
      countries: ['xx'],
      description: 'Test with invalid country code'
    },
    {
      name: 'Mixed valid/invalid',
      countries: ['us', 'xx', 'de'],
      description: 'Test with mix of valid and invalid country codes'
    }
  ];

  const results = [];

  for (const testCase of testCases) {
    console.log(`\n🔍 Testing: ${testCase.name}`);
    console.log(`📝 Description: ${testCase.description}`);
    
    try {
      const result = await makeAPICall(testCase.countries);
      results.push({
        testCase: testCase.name,
        countries: testCase.countries,
        success: true,
        projectCount: result.projectCount,
        countriesFound: result.countriesFound,
        sampleProjects: result.sampleProjects,
        responseTime: result.responseTime
      });
      
      console.log(`✅ Success: Found ${result.projectCount} projects`);
      console.log(`🌍 Countries in results: ${Array.from(result.countriesFound).join(', ') || 'None detected'}`);
      
      if (result.sampleProjects.length > 0) {
        console.log(`📋 Sample projects:`);
        result.sampleProjects.forEach((project, index) => {
          console.log(`   ${index + 1}. ${project.title} (${project.fullLocation}) - ID: ${project.id}`);
        });
      }
      
      console.log(`⏱️  Response time: ${result.responseTime}ms`);
      
    } catch (error) {
      console.log(`❌ Error: ${error.message}`);
      results.push({
        testCase: testCase.name,
        countries: testCase.countries,
        success: false,
        error: error.message
      });
    }
    
    // Rate limiting: wait 3 seconds between requests
    if (testCase !== testCases[testCases.length - 1]) {
      console.log('⏳ Waiting 3 seconds for rate limiting...');
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }

  // Generate summary report
  generateSummaryReport(results);
}

/**
 * Make API call with optional countries filter
 */
async function makeAPICall(countries = null) {
  const startTime = Date.now();
  
  // Build URL with parameters
  const params = new URLSearchParams({
    'limit': '20',
    'job_details': 'true',
    'user_details': 'true',
    'user_country_details': 'true',
    'location_details': 'true',
    'sort_field': 'time_updated',
    'sort_direction': 'desc',
    'project_statuses[]': 'active',
    'active_only': 'true'
  });

  // Add countries parameter if specified
  if (countries && countries.length > 0) {
    countries.forEach(country => {
      params.append('countries[]', country);
    });
  }

  const url = `${BASE_URL}?${params.toString()}`;
  
  console.log(`🔗 Request URL: ${url}`);
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Freelancer-OAuth-V1': FREELANCER_API_KEY,
      'Content-Type': 'application/json',
      'User-Agent': 'FreelancerBidder/1.0'
    }
  });

  const responseTime = Date.now() - startTime;

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  
  if (!data.result || !data.result.projects) {
    throw new Error('Invalid response format: missing projects data');
  }

  const projects = data.result.projects;
  const countriesFound = new Set();
  const sampleProjects = [];

  // Analyze projects
  projects.forEach((project, index) => {
    // Extract country information with enhanced location details
    let country = 'Unknown';
    let city = '';
    let region = '';
    
    if (project.owner && project.owner.location) {
      // Country information
      if (project.owner.location.country) {
        country = project.owner.location.country.name || project.owner.location.country.code || 'Unknown';
        if (project.owner.location.country.code) {
          countriesFound.add(project.owner.location.country.code.toLowerCase());
        }
      }
      
      // Additional location details (enabled by location_details=true)
      if (project.owner.location.city) {
        city = project.owner.location.city.name || '';
      }
      if (project.owner.location.administrative_area) {
        region = project.owner.location.administrative_area.name || '';
      }
    }

    // Collect sample projects (first 5) with enhanced location info
    if (index < 5) {
      let locationString = country;
      if (city && region) {
        locationString = `${city}, ${region}, ${country}`;
      } else if (city) {
        locationString = `${city}, ${country}`;
      } else if (region) {
        locationString = `${region}, ${country}`;
      }
      
      sampleProjects.push({
        id: project.id,
        title: project.title ? project.title.substring(0, 60) + (project.title.length > 60 ? '...' : '') : 'No title',
        country: country,
        city: city,
        region: region,
        fullLocation: locationString,
        countryCode: project.owner?.location?.country?.code?.toLowerCase() || 'unknown'
      });
    }
  });

  return {
    projectCount: projects.length,
    countriesFound,
    sampleProjects,
    responseTime,
    rawData: data
  };
}

/**
 * Generate and save summary report
 */
function generateSummaryReport(results) {
  console.log('\n\n📊 SUMMARY REPORT');
  console.log('='.repeat(80));
  
  const successfulTests = results.filter(r => r.success);
  const failedTests = results.filter(r => !r.success);
  
  console.log(`✅ Successful tests: ${successfulTests.length}`);
  console.log(`❌ Failed tests: ${failedTests.length}`);
  console.log(`📈 Total tests: ${results.length}\n`);

  // Analyze country filtering effectiveness
  if (successfulTests.length > 0) {
    console.log('🌍 Country Filtering Analysis:');
    console.log('-'.repeat(50));
    
    successfulTests.forEach(result => {
      if (result.countries) {
        const requestedCountries = result.countries.join(', ').toLowerCase();
        const foundCountries = Array.from(result.countriesFound).join(', ').toLowerCase();
        const filterWorked = result.countries.some(country => 
          result.countriesFound.has(country.toLowerCase())
        );
        
        console.log(`\n📍 ${result.testCase}:`);
        console.log(`   Requested: ${requestedCountries}`);
        console.log(`   Found: ${foundCountries || 'None'}`);
        console.log(`   Filter effective: ${filterWorked ? '✅ YES' : '❌ NO'}`);
        console.log(`   Projects found: ${result.projectCount}`);
      }
    });
  }

  // Save detailed results to file
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `countries_parameter_test_${timestamp}.json`;
  
  const reportData = {
    timestamp: new Date().toISOString(),
    summary: {
      totalTests: results.length,
      successfulTests: successfulTests.length,
      failedTests: failedTests.length
    },
    results: results
  };

  try {
    fs.writeFileSync(filename, JSON.stringify(reportData, null, 2));
    console.log(`\n💾 Detailed results saved to: ${filename}`);
  } catch (error) {
    console.error(`❌ Error saving results: ${error.message}`);
  }

  // Display failed tests
  if (failedTests.length > 0) {
    console.log('\n❌ Failed Tests:');
    console.log('-'.repeat(30));
    failedTests.forEach(result => {
      console.log(`• ${result.testCase}: ${result.error}`);
    });
  }

  console.log('\n🎯 Test completed successfully!');
}

// Run the test
if (require.main === module) {
  testCountriesParameter().catch(error => {
    console.error('❌ Test execution failed:', error);
    process.exit(1);
  });
}

module.exports = { testCountriesParameter, makeAPICall };
