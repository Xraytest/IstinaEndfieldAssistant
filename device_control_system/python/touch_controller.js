#!/usr/bin/env node
/**
 * MAA Touch Controller - Node.js Bridge for Python
 *
 * This script provides a command-line interface to the MAA Touch Controller
 * for use with Python subprocess calls.
 */

const MaaTouchController = require('../src/api');
const fs = require('fs');

// Parse command line arguments
const args = process.argv.slice(2);
if (args.length < 3) {
  console.error('Usage: node touch_controller.js <command> <adbPath> <deviceId> [options]');
  process.exit(1);
}

const command = args[0];
const adbPath = args[1];
const deviceId = args[2];

// Parse additional options
const options = {};
for (let i = 3; i < args.length; i += 2) {
  if (args[i].startsWith('--')) {
    const key = args[i].substring(2);
    const value = args[i + 1];
    options[key] = isNaN(value) ? value : Number(value);
  }
}

async function main() {
  let controller = null;

  try {
    // Create controller instance
    controller = await MaaTouchController.create(adbPath, deviceId);

    // Execute the requested command
    switch (command) {
      case 'connect':
        const connected = await controller.connect();
        console.log(JSON.stringify({ success: connected }));
        break;

      case 'disconnect':
        await controller.disconnect();
        console.log(JSON.stringify({ success: true }));
        break;

      case 'click':
        const clickResult = await controller.click(options.x, options.y);
        console.log(JSON.stringify({ success: clickResult }));
        break;

      case 'swipe':
        const swipeResult = await controller.swipe(
          options.x1,
          options.y1,
          options.x2,
          options.y2,
          options.duration || 200
        );
        console.log(JSON.stringify({ success: swipeResult }));
        break;

      case 'getDeviceInfo':
        const deviceInfo = await controller.getDeviceInfo();
        console.log(JSON.stringify(deviceInfo));
        break;

      default:
        throw new Error(`Unknown command: ${command}`);
    }
  } catch (error) {
    console.error(JSON.stringify({ success: false, error: error.message }));
    process.exit(1);
  }
}

main().catch(error => {
  console.error(JSON.stringify({ success: false, error: error.message }));
  process.exit(1);
});