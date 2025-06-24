const { execSync } = require('child_process');

/**
 * Reusable script to check if we've already placed a bid on any project
 * Uses the Freelancer API: GET /projects/0.1/bids/
 * Documentation: https://developers.freelancer.com/docs/projects/bids#bids-get
 * 
 * Usage: node check_bid.js <project_id>
 * Example: node check_bid.js 39537250
 */

// Load configuration from Python config.py directly
function loadConfig() {
    try {
        // Read and parse config.py values using a simple Python command
        const apiKey = execSync('python3 -c "import config; print(config.FREELANCER_API_KEY)"', { encoding: 'utf8' }).trim();
        const userId = execSync('python3 -c "import config; print(config.FREELANCER_NUMERIC_USER_ID)"', { encoding: 'utf8' }).trim();
        const apiUrl = execSync('python3 -c "import config; print(config.FL_API_BASE_URL)"', { encoding: 'utf8' }).trim();
        
        return {
            freelancer_api_key: apiKey,
            freelancer_user_id: parseInt(userId),
            fl_api_base_url: apiUrl
        };
    } catch (error) {
        console.error('❌ Error loading configuration from config.py:', error.message);
        console.error('Make sure config.py exists and contains the required values:');
        console.error('- FREELANCER_API_KEY');
        console.error('- FREELANCER_NUMERIC_USER_ID');
        console.error('- FL_API_BASE_URL');
        process.exit(1);
    }
}

class BidChecker {
    constructor(projectId = null) {
        // Load configuration from Python config file
        const config = loadConfig();
        
        this.apiUrl = config.fl_api_base_url;
        this.oauthToken = config.freelancer_api_key;
        this.userId = config.freelancer_user_id;
        this.projectId = projectId;
        
        console.log('✅ Configuration loaded from config.py');
        console.log(`🔑 API Key: ${this.oauthToken.substring(0, 10)}...`);
        console.log(`👤 User ID: ${this.userId}`);
        console.log(`🌐 API URL: ${this.apiUrl}`);
    }

    /**
     * Check if we've already placed a bid on the specified project
     */
    async checkExistingBid() {
        try {
            console.log(`🔍 Checking if bid exists for project ${this.projectId}...`);
            
            // Construct the API endpoint URL
            const url = new URL(`${this.apiUrl}/projects/0.1/bids/`);
            
            // Add query parameters
            url.searchParams.append('projects[]', this.projectId);
            url.searchParams.append('bidders[]', this.userId);
            
            console.log(`🌐 API URL: ${url.toString()}`);
            
            // Make the API request
            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'Freelancer-OAuth-V1': this.oauthToken,
                    'Content-Type': 'application/json',
                    'User-Agent': 'FreelancerBidder/1.0'
                }
            });

            console.log(`📡 Response Status: ${response.status} ${response.statusText}`);

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            return this.analyzeBidResponse(data);

        } catch (error) {
            console.error(`❌ Error checking bid:`, error);
            throw error;
        }
    }

    /**
     * Analyze the API response to determine bid status
     */
    analyzeBidResponse(data) {
        console.log(`\n🔍 ANALYZING BID RESPONSE:`);
        
        // Check if response contains bids
        if (!data.result || !data.result.bids) {
            console.log(`❌ No bids data in response`);
            return {
                hasBid: false,
                bidCount: 0,
                error: 'No bids data in response'
            };
        }

        const bids = data.result.bids;
        console.log(`📊 Total bids found: ${bids.length}`);

        if (bids.length === 0) {
            console.log(`✅ NO BID PLACED - You have not bid on project ${this.projectId}`);
            return {
                hasBid: false,
                bidCount: 0,
                message: `No bid found for project ${this.projectId}`
            };
        }

        // Analyze each bid
        const relevantBids = bids.filter(bid => {
            const isCorrectProject = bid.project_id === parseInt(this.projectId);
            const isOurBid = bid.bidder_id === this.userId;
            
            console.log(`📝 Bid ID ${bid.id}:`, {
                project_id: bid.project_id,
                bidder_id: bid.bidder_id,
                amount: bid.amount,
                period: bid.period,
                time_submitted: bid.time_submitted,
                retracted: bid.retracted,
                isCorrectProject,
                isOurBid
            });

            return isCorrectProject && isOurBid;
        });

        if (relevantBids.length > 0) {
            const bid = relevantBids[0]; // Take the first (should be only one)
            console.log(`⚠️ BID ALREADY PLACED!`);
            console.log(`💰 Bid Amount: $${bid.amount}`);
            console.log(`⏰ Bid Period: ${bid.period} days`);
            console.log(`📅 Submitted: ${new Date(bid.time_submitted * 1000).toLocaleString()}`);
            console.log(`🔄 Retracted: ${bid.retracted ? '❌ Yes' : '✅ No'}`);
            console.log(`📊 Status: ${bid.frontend_bid_status || 'unknown'}`);
            
            return {
                hasBid: true,
                bidCount: relevantBids.length,
                bidDetails: bid,
                message: `Bid already placed on project ${this.projectId}`
            };
        } else {
            console.log(`✅ NO BID PLACED - You have not bid on project ${this.projectId}`);
            return {
                hasBid: false,
                bidCount: 0,
                message: `No bid found for project ${this.projectId} from user ${this.userId}`
            };
        }
    }

    /**
     * Get additional project information
     */
    async getProjectInfo() {
        try {
            console.log(`\n📋 FETCHING PROJECT INFORMATION:`);
            
            const url = `${this.apiUrl}/projects/0.1/projects/${this.projectId}`;
            console.log(`🌐 Project API URL: ${url}`);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Freelancer-OAuth-V1': this.oauthToken,
                    'Content-Type': 'application/json',
                    'User-Agent': 'FreelancerBidder/1.0'
                }
            });

            if (!response.ok) {
                console.log(`⚠️ Project info request failed: ${response.status} ${response.statusText}`);
                return null;
            }

            const data = await response.json();
            
            if (data.result && data.result.projects && data.result.projects.length > 0) {
                const project = data.result.projects[0];
                console.log(`📄 Project Title: ${project.title}`);
                console.log(`💼 Project Type: ${project.type}`);
                console.log(`💰 Project Budget: $${project.budget?.minimum || 'N/A'} - $${project.budget?.maximum || 'N/A'}`);
                console.log(`📊 Current Bid Count: ${project.bid_stats?.bid_count || 'Unknown'}`);
                console.log(`🎯 Average Bid: $${project.bid_stats?.bid_avg || 'Unknown'}`);
                console.log(`📅 Project Posted: ${new Date(project.time_submitted * 1000).toLocaleString()}`);
                
                return project;
            }

            return null;

        } catch (error) {
            console.error(`❌ Error fetching project info:`, error);
            return null;
        }
    }

    /**
     * Run the complete bid check
     */
    async runCheck() {
        console.log(`🚀 STARTING BID CHECK`);
        console.log(`=`.repeat(50));
        
        try {
            // Check configuration
            if (!this.oauthToken) {
                throw new Error('OAuth token not found - update FREELANCER_API_KEY in config.py');
            }
            if (!this.userId) {
                throw new Error('User ID not configured - update FREELANCER_NUMERIC_USER_ID in config.py');
            }
            if (!this.projectId) {
                throw new Error('Project ID not provided - use: node check_bid.js <project_id>');
            }

            console.log(`🎯 Project ID: ${this.projectId}`);

            // Get project information first
            await this.getProjectInfo();

            // Check for existing bid
            const bidResult = await this.checkExistingBid();

            // Print final result
            console.log(`\n${'='.repeat(50)}`);
            console.log(`🎯 FINAL RESULT:`);
            console.log(`Project ID: ${this.projectId}`);
            console.log(`Has Bid: ${bidResult.hasBid ? '❌ YES' : '✅ NO'}`);
            console.log(`Message: ${bidResult.message}`);
            
            if (bidResult.hasBid && bidResult.bidDetails) {
                console.log(`Bid Amount: $${bidResult.bidDetails.amount}`);
                console.log(`Bid Period: ${bidResult.bidDetails.period} days`);
                console.log(`Submitted: ${new Date(bidResult.bidDetails.time_submitted * 1000).toLocaleString()}`);
                console.log(`Retracted: ${bidResult.bidDetails.retracted ? '❌ Yes' : '✅ No'}`);
                console.log(`Status: ${bidResult.bidDetails.frontend_bid_status || 'unknown'}`);
            }
            console.log(`${'='.repeat(50)}`);

            return bidResult;

        } catch (error) {
            console.error(`\n❌ BID CHECK FAILED:`);
            console.error(error.message);
            console.error(`${'='.repeat(50)}`);
            throw error;
        }
    }
}

// Run the test if this file is executed directly
if (require.main === module) {
    // Get project ID from command line arguments
    const projectId = process.argv[2];
    
    if (!projectId) {
        console.error('❌ Error: Project ID required');
        console.error('Usage: node check_bid.js <project_id>');
        console.error('Example: node check_bid.js 39537250');
        process.exit(1);
    }
    
    if (!/^\d+$/.test(projectId)) {
        console.error('❌ Error: Project ID must be a number');
        console.error('Example: node check_bid.js 39537250');
        process.exit(1);
    }
    
    const checker = new BidChecker(projectId);
    
    checker.runCheck()
        .then(result => {
            console.log(`\n✅ Bid check completed successfully`);
            process.exit(result.hasBid ? 1 : 0); // Exit code 1 if bid exists, 0 if no bid
        })
        .catch(error => {
            console.error(`\n❌ Bid check failed:`, error.message);
            process.exit(2); // Exit code 2 for errors
        });
}

module.exports = BidChecker; 