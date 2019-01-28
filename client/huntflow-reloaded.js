// Description:
//   Hubot script to leverage some of the Huntflow facilities
//

module.exports = async (robot) => {
  const Redis = require('ioredis')
  const routines = require('hubot-routines')

  const HUNTFLOW_REMINDER_CHANNEL = process.env.HUNTFLOW_REMINDER_CHANNEL || 'hr'
  const REDIS_CHANNEL = process.env.REDIS_CHANNEL || 'hubot-huntflow-reloaded'
  const REDIS_HOST = process.env.REDIS_HOST || '127.0.0.1'
  const REDIS_PASSWORD = process.env.REDIS_PASSWORD || null
  const REDIS_PORT = parseInt(process.env.REDIS_PORT, 10) || 16379

  const attemptsNumber = 15
  const redis = new Redis({
    host: REDIS_HOST,
    port: REDIS_PORT,
    password: REDIS_PASSWORD
  })

  if (!(await routines.isBotInRoom(robot, HUNTFLOW_REMINDER_CHANNEL))) {
    routines.rave(robot, `Hubot is not in the group or channel named '${HUNTFLOW_REMINDER_CHANNEL}'`)
    return
  }

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
    let json

    console.log(`Received the following message from ${channel}: ${message}`)

    json = JSON.parse(message)

    robot.messageRoom(HUNTFLOW_REMINDER_CHANNEL, `Кандидату ${json['first_name']} ${json['last_name']} назначено собеседование.`)
  })

  redis.subscribe(REDIS_CHANNEL, (error, count) => {
    if (error) {
      throw new Error(error)
    }

    console.log(`Subscribed to ${count} channel. Listening for updates on the ${REDIS_CHANNEL} channel.`)
  })
}
