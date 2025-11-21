module.exports = {
  rewrites: async () => {
    return [
      {
        source: '/api/chat/completions',
        destination: '/api',
      },
      {
        source: '/api/feedback',
        destination: '/api',
      },
      {
        source: '/api/models',
        destination: '/api',
      },
    ]
  },
}
