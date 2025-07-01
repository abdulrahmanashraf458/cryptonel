const http = require('http');

// Simple function to refresh the leaderboard cache
async function refreshCache() {
  return new Promise((resolve, reject) => {
    console.log('Refreshing leaderboard cache...');
    
    const options = {
      hostname: 'localhost',
      port: 5000,
      path: '/api/leaderboard/refresh',
      method: 'POST'
    };

    const req = http.request(options, res => {
      let data = '';
      
      res.on('data', chunk => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          if (response.success) {
            console.log('Leaderboard cache refreshed successfully!');
            resolve(response);
          } else {
            console.error('Error:', response.error || 'Unknown error');
            reject(new Error(response.error || 'Unknown error'));
          }
        } catch (err) {
          console.error('Error parsing response:', err);
          reject(err);
        }
      });
    });
    
    req.on('error', error => {
      console.error('Error making request:', error);
      reject(error);
    });
    
    req.end();
  });
}

// Execute the refresh
refreshCache()
  .then(() => {
    console.log('Done!');
    process.exit(0);
  })
  .catch(err => {
    console.error('Failed:', err);
    process.exit(1);
  }); 