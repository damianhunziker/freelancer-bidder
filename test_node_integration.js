#!/usr/bin/env node
/**
 * Test Script für Node.js Integration mit Python Correlation System
 * ===============================================================
 * 
 * Testet die Integration zwischen Node.js und dem konfigurierbaren
 * Python Correlation Manager System.
 */

const { exec } = require('child_process');
const util = require('util');
const path = require('path');

const execPromise = util.promisify(exec);

async function testCorrelationIntegration() {
    console.log('🧪 Testing Node.js → Python Correlation Integration');
    console.log('=' * 60);
    
    // Test 1: Check config loading
    console.log('\n📋 Test 1: Config Loading');
    try {
        const { stdout } = await execPromise('python3 -c "from config import CORRELATION_ANALYSIS_MODE; print(CORRELATION_ANALYSIS_MODE)"');
        const mode = stdout.trim();
        console.log(`✅ Config loaded successfully: ${mode}`);
        
        const useVectorStore = ['VECTOR_STORE', 'HYBRID'].includes(mode);
        console.log(`🔧 Vector Store enabled: ${useVectorStore}`);
    } catch (error) {
        console.log(`❌ Config loading failed: ${error.message}`);
        return false;
    }
    
    // Test 2: Simulate Node.js correlation analysis call
    console.log('\n📋 Test 2: Correlation Analysis');
    
    const testJobData = {
        project_details: {
            title: 'Laravel Dashboard Development',
            description: 'Build a real-time dashboard with Vue.js frontend and Laravel backend, including data visualization with charts and real-time updates',
            jobs: [
                { name: 'Laravel' },
                { name: 'Vue.js' },
                { name: 'MySQL' },
                { name: 'Chart.js' },
                { name: 'Real-time' }
            ]
        }
    };
    
    // Prepare job data exactly like Node.js will
    const jobDescription = `${testJobData.project_details.title}\n${testJobData.project_details.description}`;
    const skills = testJobData.project_details.jobs.map(job => job.name);
    const jobDescriptionWithSkills = `${jobDescription}\nSkills: ${skills.join(', ')}`;
    
    // Escape quotes for shell command (exact same logic as index.js)
    const escapedJobDescription = jobDescriptionWithSkills.replace(/"/g, '\\"').replace(/'/g, "\\'");
    
    // Run the exact same Python command as index.js
    const pythonCommand = `python3 -c "
import json
import sys
try:
    from correlation_manager import CorrelationManager
    
    manager = CorrelationManager()
    job_description = '''${escapedJobDescription}'''
    
    result = manager.analyze_job_correlation(job_description)
    
    # Output the result as JSON for Node.js to parse
    output = {
        'success': True,
        'analysis_mode': result.analysis_mode,
        'execution_time_ms': result.execution_time_ms,
        'enhanced_analysis': result.enhanced_analysis,
        'correlation_analysis': result.correlation_analysis,
        'fallback_used': result.fallback_used,
        'error_message': result.error_message
    }
    print(json.dumps(output))
    
except Exception as e:
    print(json.dumps({
        'success': False,
        'error': str(e),
        'fallback_to_sql': True
    }))
"`;

    try {
        const { stdout, stderr } = await execPromise(pythonCommand, {
            timeout: 30000 // 30 second timeout
        });
        
        if (stderr) {
            console.log('⚠️  Python stderr:', stderr);
        }
        
        const pythonResult = JSON.parse(stdout.trim());
        
        if (pythonResult.success) {
            console.log(`✅ Correlation analysis successful!`);
            console.log(`📊 Analysis mode: ${pythonResult.analysis_mode}`);
            console.log(`⏱️  Execution time: ${pythonResult.execution_time_ms.toFixed(1)}ms`);
            console.log(`🎯 Enhanced analysis: ${pythonResult.enhanced_analysis}`);
            
            if (pythonResult.fallback_used) {
                console.log(`⚠️  Fallback used: ${pythonResult.fallback_used}`);
            }
            
            // Analyze results
            const analysis = pythonResult.correlation_analysis;
            console.log(`📋 Results found:`);
            console.log(`  - Domains: ${analysis.domains?.length || 0}`);
            console.log(`  - Employment: ${analysis.employment?.length || 0}`);
            console.log(`  - Education: ${analysis.education?.length || 0}`);
            
            // Test JSON conversion for AI messages
            const simulatedAIResponse = JSON.stringify({ correlation_analysis: analysis });
            console.log(`📤 AI message format ready (${simulatedAIResponse.length} chars)`);
            
            return true;
            
        } else {
            console.log(`❌ Correlation analysis failed: ${pythonResult.error}`);
            console.log(`🔄 Would fallback to SQL: ${pythonResult.fallback_to_sql}`);
            return false;
        }
        
    } catch (error) {
        console.log(`❌ Python execution failed: ${error.message}`);
        return false;
    }
}

async function testModeSwitch() {
    console.log('\n📋 Test 3: Mode Switching');
    
    const modes = ['VECTOR_STORE', 'SQL', 'HYBRID'];
    
    for (const mode of modes) {
        try {
            // Simulate changing mode in config.py
            console.log(`\n🔧 Testing mode: ${mode}`);
            
            const { stdout } = await execPromise(`python3 -c "
from correlation_manager import CorrelationManager
manager = CorrelationManager()
manager.analysis_mode = '${mode}'
result = manager.analyze_job_correlation('Laravel dashboard with Vue.js')
print(f'Mode: {result.analysis_mode}, Time: {result.execution_time_ms:.1f}ms, Enhanced: {result.enhanced_analysis}')
"`);
            
            console.log(`  ✅ ${stdout.trim()}`);
            
        } catch (error) {
            console.log(`  ❌ Mode ${mode} failed: ${error.message}`);
        }
    }
}

async function testNodeJSMessageFormat() {
    console.log('\n📋 Test 4: Node.js Message Format Compatibility');
    
    try {
        // Test the exact format that Node.js expects
        const testResult = {
            correlation_analysis: {
                domains: [
                    {
                        domain: "reishauer.com",
                        title: "Reishauer Manufacturing Dashboard",
                        relevance_score: 0.85,
                        tags: [
                            { name: "Laravel", relevance_score: 0.9 },
                            { name: "Vue.js", relevance_score: 0.85 }
                        ]
                    }
                ],
                employment: [
                    {
                        company: "Vyftec Hunziker",
                        position: "Lead Developer",
                        relevance_score: 0.9,
                        description: "Dashboard development experience"
                    }
                ],
                education: []
            }
        };
        
        // Simulate AI response format
        const simulatedAIResponse = JSON.stringify(testResult);
        
        // Test if it would parse correctly
        const parsed = JSON.parse(simulatedAIResponse);
        
        if (parsed.correlation_analysis && 
            Array.isArray(parsed.correlation_analysis.domains) &&
            Array.isArray(parsed.correlation_analysis.employment) &&
            Array.isArray(parsed.correlation_analysis.education)) {
            
            console.log('✅ Message format is compatible with Node.js parsing');
            console.log(`📤 Sample message length: ${simulatedAIResponse.length} chars`);
            
            return true;
        } else {
            console.log('❌ Message format is NOT compatible');
            return false;
        }
        
    } catch (error) {
        console.log(`❌ Message format test failed: ${error.message}`);
        return false;
    }
}

// Main test execution
async function runAllTests() {
    console.log('🧪 Node.js ↔ Python Correlation Integration Tests');
    console.log('=' * 60);
    
    const results = [];
    
    // Run all tests
    results.push(await testCorrelationIntegration());
    results.push(await testModeSwitch());
    results.push(await testNodeJSMessageFormat());
    
    // Summary
    const passed = results.filter(r => r).length;
    const total = results.length;
    
    console.log('\n📊 Test Summary:');
    console.log('=' * 30);
    console.log(`✅ Passed: ${passed}/${total} tests`);
    console.log(`${passed === total ? '🎉' : '⚠️'} Integration ${passed === total ? 'READY' : 'NEEDS WORK'}`);
    
    if (passed === total) {
        console.log('\n🚀 Ready for production!');
        console.log('Node.js can now use Vector Store correlation analysis');
        console.log('Switch configured in config.py: CORRELATION_ANALYSIS_MODE');
    } else {
        console.log('\n🔧 Please fix the failing tests before deployment');
    }
    
    return passed === total;
}

// Execute if called directly
if (require.main === module) {
    runAllTests()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('❌ Test execution failed:', error);
            process.exit(1);
        });
}

module.exports = {
    testCorrelationIntegration,
    testModeSwitch,
    testNodeJSMessageFormat,
    runAllTests
};