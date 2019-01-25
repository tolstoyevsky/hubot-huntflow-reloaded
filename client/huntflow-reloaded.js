// Description:
//   Hubot script to leverage some of the Huntflow facilities
//

module.exports = async (robot) => {
  const Redis = require('ioredis')
  const routines = require('hubot-routines')

  const CHANNEL_NAME = process.env.CHANNEL_NAME || 'hubot-huntflow-reloaded'
  const REDIS_HOST = process.env.REDIS_HOST || '127.0.0.1'
  const REDIS_PORT = parseInt(process.env.REDIS_PORT, 10) || 16379

  const attemptsNumber = 15
  const redis = new Redis({
    host: REDIS_HOST,
    port: REDIS_PORT
  })

  let connected = false

  for (let i = 0; i < attemptsNumber; i++) {
    if (redis.status === 'ready') {
      connected = true
      break
    }

    await routines.delay(1000)
  }

  if (!connected) {
    routines.rave(robot, `Could not connect to Redis`)
    return
  }

  redis.on('message', (channel, message) => {
    console.log(`Received the following message from ${channel}: ${message}`)
  })

  redis.subscribe(CHANNEL_NAME, (error, count) => {
    if (error) {
      throw new Error(error)
    }

    console.log(`Subscribed to ${count} channel. Listening for updates on the ${CHANNEL_NAME} channel.`)
  })
}
