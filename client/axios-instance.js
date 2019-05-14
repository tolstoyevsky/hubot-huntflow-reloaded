const axios = require('axios')
const utils = require('./utils')

// handling authorization tokens
let accessToken
let refreshToken

const setAccessToken = (token) => {
  accessToken = token
}

const setTokens = (tokens) => {
  setAccessToken(tokens.access)
  refreshToken = tokens.refresh
}

// init axios instance with base url
const instance = axios.create({
  errorHandle: false,
  baseURL: utils.BASE_SERVER_URL,
  timeout: 1000
})

/**
 * Function for getting  access token
 * @returns {Promise<void>}
 */
const getAccessToken = async () => {
  const data = await instance.post('/token',
    { user: { email: utils.SERVER_USER_EMAIL, password: utils.SERVER_USER_PASSWORD } })
  setTokens(data.data)
}

/**
 * Function for refreshing access token
 * @returns {Promise<void>}
 */
const refreshAccessToken = async () => {
  const data = await instance.post(`/token/refresh?refresh=${refreshToken}`)
  setAccessToken(data.data.access)
}

/**
 * Function to retry original request if request had status 401/403 initially
 * @param request
 * @returns {Promise<any>}
 */
const processAccessToken = request => {
  request.params = { access: accessToken }
  request._retry = true
  return Promise.resolve(axios(request))
}

// Adding access token to authorized requests
instance.interceptors.request.use(request => {
  if (!request.url.match(/^\/token/)) {
    request.params = { access: accessToken }
  }
  return request
}, error => {
  return Promise.reject(error)
})

instance.interceptors.response.use(response => {
  return response
}, async error => {
  if (error.config.url.match(/\/token/)) return Promise.reject(error)

  const originalRequest = error.config
  if (originalRequest._retry) return Promise.reject(error)

  if (error.response.status === 403) {
    try {
      await refreshAccessToken()
      return processAccessToken(originalRequest)
    } catch (error) {
      if (error.response.data.detail === 'Refresh token is expired') {
        await getAccessToken()
        return processAccessToken(originalRequest)
      }
    }
  } else if (error.response.status === 401) {
    await getAccessToken()
    return processAccessToken(originalRequest)
  }

  return Promise.reject(error)
})

module.exports = instance
