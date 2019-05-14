'use strict'

const path = require('path')

module.exports = (robot) => {
  const scriptsPath = path.resolve(__dirname, 'client')
  robot.loadFile(scriptsPath, 'huntflow-reloaded.js')
  robot.loadFile(scriptsPath, 'interview-controller.js')
}
