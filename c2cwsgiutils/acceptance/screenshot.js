import puppeteer from 'puppeteer';
import { program } from 'commander';

program
  .option('--url <char>', 'The URL')
  .option('--output <char>', 'The output filename')
  .option('--width <int>', 'The page width', 800)
  .option('--height <int>', 'The page height', 600)
  .option('--sleep <int>', 'Sleep that the page is fully loaded [ms]', 0)
  .option('--headers <str>', 'The headers', '{}')
  // see: https://pptr.dev/api/puppeteer.page.emulatemediafeatures
  .option('--media <str>', 'The media feature, see Page.emulateMediaFeatures', '[]');

program.parse();

const options = program.opts();

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-web-security'],
  });
  const page = await browser.newPage();
  page.setDefaultNavigationTimeout(60000);
  await page.setExtraHTTPHeaders(JSON.parse(options.headers));
  await page.emulateMediaFeatures(JSON.parse(options.media));

  page.on('console', async (msg) => {
    const msgArgs = msg.args();
    for (let i = 0; i < msgArgs.length; ++i) {
      console.log(await msgArgs[i].jsonValue());
    }
  });
  page.on('error', (err) => {
    console.log('error', err);
  });
  page.on('pageerror', (err) => {
    console.log('pageerror', err);
  });
  page.on('requestfailed', (request) => {
    console.log('requestfailed on URL:', request.url());
    console.log(request.failure());
    const response = request.response();
    if (response !== null) {
      console.log(response);
      console.log(response.status());
      console.log(response.statusText());
      console.log(response.text());
    }
  });

  await page.setViewport({
    width: parseInt(options.width),
    height: parseInt(options.height),
  });
  await page.goto(options.url, { timeout: 60000 });

  await new Promise((r) => setTimeout(r, parseInt(options.sleep)));
  await page.screenshot({
    path: options.output,
    clip: { x: 0, y: 0, width: parseInt(options.width), height: parseInt(options.height) },
  });
  await browser.close();
})();
