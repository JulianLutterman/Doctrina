module.exports = {
  rewrites: async () => {
    return [
      {
        source: '/api/chat/completions',
        destination: '/api/chat/completions',
      },
      {
        source: '/api/feedback',
        destination: '/api/feedback',
      },
      {
        source: '/api/models',
        destination: '/api/models',
      },
    ]
  },
}
