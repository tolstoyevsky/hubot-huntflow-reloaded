const moment = require('moment')

// init exports instance
const exp = module.exports = {}

// env consts
exp.BASE_SERVER_URL = process.env.BASE_SERVER_URL || 'http://127.0.0.1:8888'
exp.SERVER_USER_EMAIL = process.env.SERVER_USER_EMAIL
exp.SERVER_USER_PASSWORD = process.env.SERVER_USER_PASSWORD

// messages constants
exp.MSG_PERMISSION_DENIED = 'У тебя недостаточно прав для этой команды :rolling_eyes:'
exp.MSG_NOT_ANY_SCHEDULED_INTERVIEWS = 'Запланированных интервью нет.'
exp.MSG_ERROR_TRY_AGAIN = 'Произошла ошибка, попробуйте еще раз.'
exp.MSG_SUCCESSFULLY_DELETED = 'Успешно удалено.'
exp.MSG_AUTHORIZATION_DATA_NEEDED = 'SERVER_USER_EMAIL and SERVER_USER_PASSWORD ' +
  'are mandatory parameters, however they\'re not specified.'
exp.MSG_CHOOSE_CANDIDATE = 'Выберите одного из кандидатов, чтобы удалить интервью:'

exp.ERROR_MSGS_FROM_SERVER = {
  'invalid_auth_creds': 'Авторизация не удалась, обратитесь к администратору Rocket.Chat.',
  'no_candidate': 'Кандидат с такими данными не был найден.',
  'no_interview': 'У данного кандидата нет запланированного интервью.'
}

/**
 * @param {InterviewEvent} json
 * @returns {string}
 */
const makeMessageFromEventJSON = (json) => {
  const time = moment(json.start).format('HH:mm')
  let message = `${time} - ${json.first_name} ${json.last_name}`

  if (json.type === 'rescheduled-interview') {
    message += ' (перенесено)'
  }

  return message
}

/**
 * @param {Array<InterviewEvent>} data
 * @returns {string}
 */
exp.buildReport = (data) => {
  const body = {
    'через час': [],
    'сегодня': [],
    'завтра': []
  }

  // Parse data
  for (const item of data) {
    if (item.type === 'fwd') {
      let fwd = moment(item.employment_date)
      const amount = fwd.diff(moment().startOf('day'), 'days')

      const when = (amount) => {
        if (amount === 1) {
          return 'завтра'
        }
        if (amount === 0) {
          return 'сегодня'
        }
        return fwd.format('DD.MM')
      }
      return `${item.first_name} ${item.last_name} выходит на работу ${when(amount)}.`
    }

    const now = moment()
    const start = moment(item.start)

    if (start.isBefore(now)) continue

    const diff = start.clone().startOf('day')
      .diff(now.clone().startOf('day'), 'days')

    switch (diff) {
      case 0:
        const minutesDiff = start.clone().diff(now, 'minutes')
        if (minutesDiff <= 60) {
          body['через час'].push(makeMessageFromEventJSON(item))
        } else {
          body['сегодня'].push(makeMessageFromEventJSON(item))
        }
        break
      case 1:
        body['завтра'].push(makeMessageFromEventJSON(item))
        break
      default:
        const date = start.format('DD.MM')
        body[date] = body[date] || []
        body[date].push(makeMessageFromEventJSON(item))
    }
  }

  // Create report message
  let report = ''
  for (const key in body) {
    const value = body[key]

    if (!value.length) continue

    const prefix = value.length > 1 ? 'Собеседования' : 'Собеседование'

    report += `${prefix} ${key}:\n`
    report += value.join('\n')
    report += '\n\n'
  }

  return report.trim()
}
