// Description:
//   A Hubot script which helps hrs to control interviews.
//
// Commands:
//  begin group Huntflow Reloaded
//    begin admin
//      hubot удалить интервью - removes the non-expired interview of the specified candidate
//    end admin
//  end group
//

const routines = require('hubot-routines')
const utils = require('./utils')

const interviewsService = require('./interviews-service')

const deleteCandidateRegExp = new RegExp(/(удалить интервью кандидата)\s(((([А-Яа-я]+)|([A-Za-z]+))\s?){2})\s*/i)

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
      message = candidates.length === 0 ? utils.MSG_NOT_ANY_SCHEDULED_INTERVIEWS : buildCandidatesButtons(candidates)
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
    } catch (error) {
      if (error.response.status === 400) message = getServerTranslatedMessage(error.response.data.code)
      routines.rave(robot, error.message)
    }

    return msg.send(message)
  })
}

function buildCandidatesButtons (users) {
  const usersArray = users.map(function (user) {
    const username = `${user.last_name} ${user.first_name}`
    return [username, `Удалить интервью кандидата ${username}`]
  })

  return routines.buildMessageWithButtons(
    utils.MSG_CHOOSE_CANDIDATE,
    usersArray
  )
}

function getServerTranslatedMessage (code) {
  return utils.ERROR_MSGS_FROM_SERVER[code]
}
