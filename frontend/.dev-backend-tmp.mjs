
process.env.FCM_DEV = '1'
import { startWebServer } from './web/server.js'
startWebServer(3333, { open: false, startPingLoop: true }).then(() => {}).catch(console.error)
