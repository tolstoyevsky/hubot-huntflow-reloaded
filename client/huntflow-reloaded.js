// Description:
//   Hubot script to leverage some of the Huntflow facilities
//

module.exports = async (robot) => {
  const Redis = require('ioredis')
  const routines = require('hubot-routines')

  const utils = require('./utils')

  const HUNTFLOW_REMINDER_CHANNEL = process.env.HUNTFLOW_REMINDER_CHANNEL || 'hr'
  const REDIS_CHANNEL = process.env.REDIS_CHANNEL || 'hubot-huntflow-reloaded'
  const REDIS_HOST = process.env.REDIS_HOST || '127.0.0.1'
  const REDIS_PASSWORD = process.env.REDIS_PASSWORD || null
  const REDIS_PORT = parseInt(process.env.REDIS_PORT, 10) || 16379

  const attemptsNumber = 15
  const redis = new Redis({
    host: REDIS_HOST,
    port: REDIS_PORT,
    password: REDIS_PASSWORD,
    retryStrategy (times) {
      return times < attemptsNumber ? Math.min(times * 100, 2000) : false
    }
  })

  if (!(await routines.isBotInRoom(robot, HUNTFLOW_REMINDER_CHANNEL))) {
    routines.rave(robot, `Hubot is not in the group or channel named '${HUNTFLOW_REMINDER_CHANNEL}'`)
    return
  }

  redis.on('end', () => robot.logger.info('Redis connection is closed'))

  redis.on('reconnecting', time => robot.logger.info(`Could not connect to Redis. Retying after ${time}ms...`))

  redis.on('error', (err) => {
    // There is no need to print here some of the error codes.
    switch (err.errno) {
      case 'ECONNREFUSED':
        break
      default:
        routines.rave(robot, `Redis error:\n${err.message}`)
        break
    }
  })

  redis.on('message', (channel, message) => {
    let json

    robot.logger.info(`Received the following message from ${channel}: ${message}`)

    json = JSON.parse(message)

    const output = utils.buildReport([json])

    if (output) {
      robot.messageRoom(HUNTFLOW_REMINDER_CHANNEL, output)
    }
  })

  redis.subscribe(REDIS_CHANNEL, (error, count) => {
    if (error) {
      return redis.disconnect()
    }

    robot.logger.info(`Subscribed to ${count} channel. Listening for updates on the ${REDIS_CHANNEL} channel.`)
  })
}
