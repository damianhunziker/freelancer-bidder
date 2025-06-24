# Freelancer Bid Checker Tools

This directory contains tools to check if you have already placed bids on Freelancer projects using the Freelancer API.

## Files

### `check_bid.js` - Reusable Bid Checker
**Usage:** `node check_bid.js <project_id>`

A command-line tool that checks if you've already placed a bid on any project.

**Examples:**
```bash
# Check if you've bid on project 39537250
node check_bid.js 39537250

# Check any project ID
node check_bid.js 12345678
```

**Exit Codes:**
- `0` = No bid found ✅
- `1` = Bid already exists ❌  
- `2` = Error occurred ⚠️

### `test_bid_check.js` - Specific Test
A test script specifically for project 39537250. Run with:
```bash
node test_bid_check.js
```

## Configuration

Both tools automatically load configuration from `config.py`:

```python
# Required configuration in config.py
FREELANCER_API_KEY = "your_oauth_token_here"           # OAuth token
FREELANCER_NUMERIC_USER_ID = 3953491                   # Your numeric user ID
FL_API_BASE_URL = "https://www.freelancer.com/api"     # API base URL
```

## Features

### ✅ Comprehensive Information
- **Bid Details**: Amount, period, submission date
- **Project Info**: Title, budget, bid count, average bid
- **Status Check**: Active, retracted, or completed bids
- **Rate Limits**: Shows remaining API calls

### ✅ Smart Analysis
- Filters bids by project ID and your user ID
- Handles multiple bids per project
- Shows detailed bid analysis and timestamps
- Provides clear success/failure indicators

### ✅ Error Handling
- Configuration validation
- API error handling
- Network timeout handling
- Clear error messages

## API Documentation

Uses the Freelancer API endpoint:
- **Endpoint**: `GET /projects/0.1/bids/`
- **Documentation**: https://developers.freelancer.com/docs/projects/bids#bids-get
- **Authentication**: OAuth token via `Freelancer-OAuth-V1` header

## Output Example

```
🚀 STARTING BID CHECK
==================================================
✅ Configuration loaded from config.py
🔑 API Key: xDC4VKOJ6t...
👤 User ID: 3953491
🌐 API URL: https://www.freelancer.com/api
🎯 Project ID: 39537250

📋 FETCHING PROJECT INFORMATION:
📄 Project Title: WordPress Custom Development
💼 Project Type: fixed
💰 Project Budget: $250 - $750
📊 Current Bid Count: 15
🎯 Average Bid: $420

🔍 ANALYZING BID RESPONSE:
📊 Total bids found: 1
📝 Bid ID 456310474: {
  project_id: 39537250,
  bidder_id: 3953491,
  amount: 252,
  period: 14,
  time_submitted: 1750649596,
  retracted: false
}

⚠️ BID ALREADY PLACED!
💰 Bid Amount: $252
⏰ Bid Period: 14 days
📅 Submitted: 6/23/2025, 10:33:16 AM
🔄 Retracted: ✅ No
📊 Status: active

==================================================
🎯 FINAL RESULT:
Project ID: 39537250
Has Bid: ❌ YES
Message: Bid already placed on project 39537250
==================================================
```

## Troubleshooting

### Configuration Issues
```bash
❌ Error loading configuration from config.py
Make sure config.py exists and contains the required values:
- FREELANCER_API_KEY
- FREELANCER_NUMERIC_USER_ID
- FL_API_BASE_URL
```

**Solution:** Update your `config.py` file with the correct values.

### API Authentication Issues
```bash
📡 Response Status: 401 Unauthorized
```

**Solution:** Your OAuth token may be expired. Generate a new token at https://developers.freelancer.com/

### Rate Limiting
```bash
📡 Response Status: 429 Too Many Requests
```

**Solution:** Wait a few minutes before making more API calls. The tools show remaining API calls in the headers.

## Integration

These tools can be integrated into larger automation scripts:

```bash
#!/bin/bash
# Check if bid exists before placing a new one
if node check_bid.js 39537250; then
    echo "No existing bid found, proceeding with bidding..."
    # Your bidding logic here
else
    echo "Bid already exists, skipping..."
fi
``` 