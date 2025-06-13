// Calculate check interval based on project age
function calculateCheckInterval(projectAgeInDays) {
    // For projects less than 1 day old, check every 20 seconds
    if (projectAgeInDays < 1) {
        return 20 * 1000; // 20 seconds
    }
    
    // For projects older than 7 days, check every 2 hours
    if (projectAgeInDays >= 7) {
        return 2 * 60 * 60 * 1000; // 2 hours
    }
    
    // For projects between 1 and 7 days old, use a logarithmic scale
    // This will gradually increase the interval as the project gets older
    const minInterval = 20 * 1000; // 20 seconds
    const maxInterval = 2 * 60 * 60 * 1000; // 2 hours
    const scale = Math.log(maxInterval / minInterval) / 6; // 6 days between min and max
    
    return Math.round(minInterval * Math.exp(scale * projectAgeInDays));
}

// Update the checkProject function to use dynamic intervals
async function checkProject(projectId) {
    try {
        const response = await fetch(`https://www.freelancer.com/api/projects/0.1/projects/${projectId}/?job_details=true&user_details=true&user_country_details=true&user_hourly_rate_details=true&user_status_details=true&hourly_project_info=true&upgrade_details=true&full_description=true&reputation=true&attachment_details=true&employer_reputation=true&bid_details=true&profile_description=true&sort_field=time_updated&sort_direction=desc&project_statuses[]=active&active_only=true&compact=true&or_search_query=true&jobs=true`, {
            headers: {
                'freelancer-oauth-v1': process.env.FREELANCER_API_KEY
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const project = data.result;

        // Calculate project age in days
        const submitDate = new Date(project.submitdate * 1000);
        const now = new Date();
        const projectAgeInDays = (now - submitDate) / (1000 * 60 * 60 * 24);

        // Calculate next check interval based on project age
        const nextCheckInterval = calculateCheckInterval(projectAgeInDays);

        // Update the project's check interval
        projectCheckIntervals.set(projectId, nextCheckInterval);

        // Log the current check interval
        console.log(`Project ${projectId} (${projectAgeInDays.toFixed(1)} days old) - Next check in ${(nextCheckInterval / 1000).toFixed(0)} seconds`);

        // Process the project data as before
        if (project.bid_stats && project.bid_stats.bid_count !== undefined) {
            const bidCount = project.bid_stats.bid_count;
            console.log(`Project ${projectId} has ${bidCount} bids`);

            // Your existing bid count processing logic here
            // ...

        } else {
            console.log(`No bid count available for project ${projectId}`);
        }

    } catch (error) {
        console.error(`Error checking project ${projectId}:`, error);
    }
} 