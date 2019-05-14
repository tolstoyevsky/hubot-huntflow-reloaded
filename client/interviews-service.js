const instance = require('./axios-instance')

const exp = module.exports = {}

exp.getCandidatesList = async () => {
  return instance.get('/manage/list')
}

exp.deleteCandidateInterview = async (candidate) => {
  return instance.post('/manage/delete', { candidate })
}
