const moment = require('moment')

/**
 * @param {InterviewEvent} json
 * @returns {string}
 */
function makeMessageFromEventJSON (json) {
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
function buildReport (data) {
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

module.exports = { buildReport, makeMessageFromEventJSON }
