const instance = require('./axios-instance')

function getFWDList () {
  return instance.get('/manage/fwd_list')
}

function getFWDUser (body) {
  const uri = encodeURI(
    `/manage/fwd?first_name=${body.first_name}&last_name=${body.last_name}`
  )
  return instance.get(uri)
}

module.exports = { getFWDList, getFWDUser }
