// Description:
//   A Hubot script which helps hrs to control interviews.
//
// Commands:
//  begin group Huntflow Reloaded
//    hubot когда выйдет - shows list with people who are coming to work soon
//    begin admin
//      hubot удалить интервью - removes the non-expired interview of the specified candidate
//    end admin
//  end group
//

const routines = require('hubot-routines')
const moment = require('moment')
const utils = require('./utils')

const interviewsService = require('./interviews-service')
const fwdService = require('./fwd-service')

const deleteCandidateRegExp = new RegExp(/(удалить интервью кандидата)\s(((([А-Яа-яЁё]+)|([A-Za-zЁё]+))\s?){2})\s*/i)

module.exports = async (robot) => {
  // Checking if server user email & password was specified
  if (!utils.SERVER_USER_EMAIL || !utils.SERVER_USER_PASSWORD) {
    routines.rave(robot, utils.MSG_AUTHORIZATION_DATA_NEEDED)
    return
  }

  robot.respond(/(удалить интервью)\s*$/i, async (msg) => {
    if (!await routines.isAdmin(robot, msg.message.user.name.toString())) {
      msg.send(utils.MSG_PERMISSION_DENIED)
      return
    }

    let message = utils.MSG_ERROR_TRY_AGAIN

    try {
      const response = await interviewsService.getCandidatesList()
      const candidates = response.data.users
      message = candidates.length === 0 ? utils.MSG_NOT_ANY_SCHEDULED_INTERVIEWS : buildCandidatesButtons(candidates, msg.robot.alias)
    } catch (error) {
      if (error.response.status === 400) message = getServerTranslatedMessage(error.response.data.code)
      routines.rave(robot, error.message)
    }

    return msg.send(message)
  })

  robot.respond(deleteCandidateRegExp, async (msg) => {
    let message = utils.MSG_ERROR_TRY_AGAIN

    try {
      const text = msg.match[0]
      const candidate = text.split(' ').splice(4) // get elements after word 'кандидата'
      await interviewsService.deleteCandidateInterview({ first_name: candidate[1], last_name: candidate[0] })
      message = utils.MSG_SUCCESSFULLY_DELETED
      const roomName = msg.envelope.message.room
      if (roomName !== utils.HUNTFLOW_REMINDER_CHANNEL) {
        robot.messageRoom(
          utils.HUNTFLOW_REMINDER_CHANNEL,
          `Собеседование кандидата ${candidate[0]} ${candidate[1]} было удалено пользователем @${msg.message.user.name}`
        )
      }
    } catch (error) {
      if (error.response.status === 400) message = getServerTranslatedMessage(error.response.data.code)
      routines.rave(robot, error.message)
    }

    return msg.send(message)
  })

  robot.respond(/когда выйдет\s*$/i, (msg) => {
    fwdService.getFWDList()
      .then(response => {
        if (response.data.total) {
          const { users } = response.data
          const buttons = routines.buildMessageWithButtons(
            'Кто из этих замечательных людей?',
            users.map(user => [
              `${user.first_name} ${user.last_name}`,
              `${msg.robot.alias} когда выйдет ${user.first_name} ${user.last_name}`
            ])
          )
          msg.send(buttons)
        } else {
          msg.send(utils.MSG_NOT_ANY_FWD_USER)
        }
      })
      .catch(err => {
        if (err.response && err.response.status === 400) {
          msg.send(getServerTranslatedMessage(err.response.data.code))
        } else {
          msg.send(utils.MSG_ERROR_TRY_AGAIN)
        }
        routines.rave(robot, err.message)
      })
  })

  robot.respond(/когда выйдет (([а-яёa-z]+\s*)+)/i, (msg) => {
    const [first_name, last_name] = msg.match[1].split(' ') // eslint-disable-line camelcase
    const candidate = { first_name, last_name }

    fwdService.getFWDUser(candidate)
      .then(response => {
        const { first_name, last_name, fwd } = response.data.candidate // eslint-disable-line camelcase
        const date = moment(fwd, 'YYYY-MM-DD').format('DD.MM')
        msg.send(`${first_name} ${last_name} выходит на работу ${date}.`) // eslint-disable-line camelcase
      })
      .catch(err => {
        if (err.response && err.response.status === 400) {
          msg.send(getServerTranslatedMessage(err.response.data.code))
        } else {
          msg.send(utils.MSG_ERROR_TRY_AGAIN)
        }
        routines.rave(robot, err.message)
      })
  })
}

function buildCandidatesButtons (users, robotName) {
  const usersArray = users.map(function (user) {
    const username = `${user.last_name} ${user.first_name}`
    return [username, `${robotName} удалить интервью кандидата ${username}`]
  })

  return routines.buildMessageWithButtons(
    utils.MSG_CHOOSE_CANDIDATE,
    usersArray
  )
}

function getServerTranslatedMessage (code) {
  return utils.ERROR_MSGS_FROM_SERVER[code] || 'Неизвестная ошибка. Попробуйте еще раз'
}
