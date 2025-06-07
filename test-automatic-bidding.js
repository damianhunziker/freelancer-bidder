const fs = require('fs').promises;
const path = require('path');

async function testAutomaticBidding() {
  console.log('🧪 Testing Automatic Bidding System...\n');
  
  try {
    // Check if jobs directory exists
    const jobsDir = path.join(__dirname, 'jobs');
    const files = await fs.readdir(jobsDir);
    const jobFiles = files.filter(file => file.startsWith('job_') && file.endsWith('.json'));
    
    console.log(`📁 Found ${jobFiles.length} job files in jobs directory`);
    
    if (jobFiles.length === 0) {
      console.log('❌ No job files found. Please run bidder.py first to generate some projects.');
      return;
    }
    
    // Analyze each project for automatic bidding eligibility
    let qualifyingProjects = 0;
    let recentProjects = 0;
    let projectsWithBidText = 0;
    let alreadyBidProjects = 0;
    
    for (const filename of jobFiles.slice(0, 10)) { // Check first 10 projects
      const filePath = path.join(jobsDir, filename);
      const content = await fs.readFile(filePath, 'utf8');
      const project = JSON.parse(content);
      
      const projectId = project.project_details?.id || 'unknown';
      const title = project.project_details?.title || 'Unknown Title';
      const flags = project.project_details?.flags || {};
      
      console.log(`\n📋 Project ${projectId}: "${title}"`);
      
      // Check age (recent = ≤ 60 minutes)
      const createdTime = new Date(project.project_details?.time_submitted * 1000);
      const ageInMinutes = (Date.now() - createdTime.getTime()) / (1000 * 60);
      const isRecent = ageInMinutes <= 60;
      
      if (isRecent) recentProjects++;
      
      console.log(`   ⏰ Age: ${Math.round(ageInMinutes)} minutes (Recent: ${isRecent})`);
      
      // Check flags
      const hasQualityFlag = flags.is_corr || flags.is_rep || flags.is_authentic || flags.is_enterprise;
      const hasUrgencyFlag = flags.is_high_paying || flags.is_urgent || flags.is_german;
      
      console.log(`   🏷️  Quality flags: ${hasQualityFlag} (corr:${!!flags.is_corr}, rep:${!!flags.is_rep}, auth:${!!flags.is_authentic}, corp:${!!flags.is_enterprise})`);
      console.log(`   🚨 Urgency flags: ${hasUrgencyFlag} (pay:${!!flags.is_high_paying}, urg:${!!flags.is_urgent}, ger:${!!flags.is_german})`);
      
      // Check if already bid
      const alreadyBid = project.buttonStates?.bidSubmitted || project.buttonStates?.applicationSent;
      if (alreadyBid) alreadyBidProjects++;
      
      console.log(`   📤 Already bid: ${alreadyBid}`);
      
      // Check if has bid text
      const hasBidText = !!project.ranking?.bid_teaser;
      if (hasBidText) projectsWithBidText++;
      
      console.log(`   📝 Has bid text: ${hasBidText}`);
      
      // Check if qualifies for automatic bidding
      const qualifiesForAutoBid = hasQualityFlag && hasUrgencyFlag && !alreadyBid;
      const qualifiesWithRecentFilter = qualifiesForAutoBid && isRecent;
      
      if (qualifiesForAutoBid) qualifyingProjects++;
      
      console.log(`   ✅ Qualifies for auto-bid: ${qualifiesForAutoBid}`);
      console.log(`   🕐 Qualifies with recent filter: ${qualifiesWithRecentFilter}`);
      
      if (qualifiesWithRecentFilter) {
        console.log(`   🎯 THIS PROJECT SHOULD BE AUTO-BID!`);
      }
    }
    
    console.log(`\n📊 Summary:`);
    console.log(`   Total projects analyzed: ${Math.min(jobFiles.length, 10)}`);
    console.log(`   Recent projects (≤60 min): ${recentProjects}`);
    console.log(`   Projects with quality+urgency flags: ${qualifyingProjects}`);
    console.log(`   Projects with existing bid text: ${projectsWithBidText}`);
    console.log(`   Already bid projects: ${alreadyBidProjects}`);
    
    console.log(`\n💡 Recommendations:`);
    if (recentProjects === 0) {
      console.log(`   ⚠️  No recent projects found. Try running bidder.py to get fresh projects.`);
    }
    if (qualifyingProjects === 0) {
      console.log(`   ⚠️  No projects qualify for automatic bidding (need both quality and urgency flags).`);
    }
    if (qualifyingProjects > 0 && recentProjects > 0) {
      console.log(`   ✅ System should work! Enable "Automatic Bidding" and "Recent Only" in the frontend.`);
    }
    
  } catch (error) {
    console.error('❌ Error testing automatic bidding:', error);
  }
}

testAutomaticBidding(); 