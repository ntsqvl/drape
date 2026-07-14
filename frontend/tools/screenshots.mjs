// Capture submission screenshots against the running dev servers.
// Usage: node tools/screenshots.mjs   (backend on 8321, frontend on 5321, mock or live)
// Output: docs/screenshots/*.png

import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = 'http://localhost:5321'
const OUT = new URL('../../docs/screenshots/', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })

const shot = (name, opts = {}) => page.screenshot({ path: `${OUT}${name}.png`, ...opts })

// 1. upload screen
await page.goto(BASE)
// Freeze animations: full-page capture re-triggers delayed keyframes,
// which shot the swatch fan mid-flight (i.e. invisible).
await page.addStyleTag({ content: '*{animation:none!important;transition:none!important}' })
await page.waitForSelector('.mirror')
await page.waitForTimeout(600) // fonts
await shot('01-upload', { fullPage: true })

// 2. start a demo persona session; catch the trace mid-flight
await page.click('.persona-chip') // amber
await page.waitForSelector('.trace-line', { timeout: 15000 })
await page.waitForFunction(() => document.querySelectorAll('.trace-line').length >= 5, null, { timeout: 20000 })
await shot('02-session-trace')

// 3. verdict (auto-advances when done)
await page.waitForSelector('.verdict-season', { timeout: 60000 })
await page.waitForTimeout(1600) // reveal + fan animations
await shot('03-verdict', { fullPage: true })

// 4. interactive draping room: click the second swatch, wait for the mirror
await page.click('.fan-card:nth-child(2)')
await page.waitForFunction(
  () => !document.querySelector('.reveal-loading'),
  null, { timeout: 60000 },
)
await page.waitForTimeout(400)
const reveal = await page.$('.reveal')
await reveal.screenshot({ path: `${OUT}04-draping-room.png` })

// 5. shop with garment check
await page.click('.verdict-actions .btn-primary')
await page.waitForSelector('.rack-card')
await page.waitForTimeout(400)
await shot('05-shop', { fullPage: true })

// 6. mobile verdict
await page.setViewportSize({ width: 390, height: 844 })
await page.click('.shop-back')
await page.waitForSelector('.verdict-season')
await page.waitForTimeout(800)
await shot('06-mobile-verdict', { fullPage: true })

await browser.close()
console.log(`wrote screenshots to ${OUT}`)
