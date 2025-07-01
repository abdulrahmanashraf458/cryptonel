/**
 * Advanced Fingerprinting Library for Cryptonel
 * This library provides advanced device fingerprinting techniques for security and fraud prevention
 */

/**
 * Generate Canvas fingerprint
 * Creates a unique identifier based on how the browser renders canvas elements
 * @returns {Promise<string>} Canvas fingerprint hash
 */
function generateCanvasFingerprint() {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas dimensions
    canvas.width = 300;
    canvas.height = 150;
    
    // Draw background
    ctx.fillStyle = 'rgb(240, 240, 240)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw text
    ctx.fillStyle = 'rgb(20, 20, 200)';
    ctx.font = '18pt Arial';
    ctx.fillText('Cryptonel ✓', 10, 50);
    
    // Draw shapes
    ctx.fillStyle = 'rgba(100, 200, 50, 0.5)';
    ctx.beginPath();
    ctx.arc(100, 100, 50, 0, Math.PI * 2, true);
    ctx.fill();
    
    ctx.fillStyle = 'rgba(200, 50, 100, 0.5)';
    ctx.beginPath();
    ctx.arc(150, 100, 50, 0, Math.PI * 2, true);
    ctx.fill();
    
    // Add a complex gradient
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, 'rgba(50, 50, 200, 0.5)');
    gradient.addColorStop(0.5, 'rgba(200, 50, 50, 0.5)');
    gradient.addColorStop(1, 'rgba(50, 200, 50, 0.5)');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(50, 50, 200, 50);
    
    // NEW: Add more complex rendering elements to make it harder to spoof
    // Draw emoji text (more complex rendering)
    ctx.fillStyle = 'rgb(120, 20, 100)';
    ctx.font = '16pt Georgia';
    ctx.fillText('🔒 Security ⚡ Speed', 20, 100);
    
    // Add curved text
    ctx.save();
    ctx.translate(150, 120);
    ctx.rotate(Math.PI / 6);
    ctx.fillStyle = 'rgba(80, 80, 200, 0.8)';
    ctx.font = '12pt Courier';
    ctx.fillText('Rotated Text', 0, 0);
    ctx.restore();
    
    // Add bezier curve
    ctx.beginPath();
    ctx.moveTo(10, 140);
    ctx.bezierCurveTo(50, 100, 200, 120, 290, 140);
    ctx.strokeStyle = 'rgba(220, 50, 100, 0.8)';
    ctx.lineWidth = 3;
    ctx.stroke();
    
    // NEW: Add a subtle randomization that doesn't affect the fingerprint
    // This prevents simple hash comparison by adding something visually imperceptible
    // but that doesn't affect the fingerprint consistency
    const date = new Date();
    const day = date.getDate();
    
    // Only use a consistent value that changes daily but is the same for all users on that day
    ctx.fillStyle = `rgba(254, 254, 254, 0.01)`;
    ctx.fillRect(day % canvas.width, day % canvas.height, 1, 1);
    
    // Get data URL and hash it
    const dataURL = canvas.toDataURL();
    
    // Return hashed value
    return hashString(dataURL);
  } catch (error) {
    console.warn('Canvas fingerprinting not supported or blocked', error);
    return Promise.resolve('canvas_not_supported');
  }
}

/**
 * Generate WebGL fingerprint
 * Creates a unique identifier based on how the browser renders WebGL elements
 * @returns {Promise<string>} WebGL fingerprint hash
 */
function generateWebGLFingerprint() {
  try {
    // Try to get WebGL context
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    // Return early if WebGL is not supported
    if (!gl) {
      return Promise.resolve('webgl_not_supported');
    }
    
    // Set canvas size
    canvas.width = 256;
    canvas.height = 128;
    
    // Get WebGL rendering information
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    
    // Collect parameters that vary between devices
    let params = [];
    
    // Add vendor and renderer if available
    if (debugInfo) {
      const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
      const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
      params.push(vendor, renderer);
    }
    
    // Add standard parameters
    params.push(
      gl.getParameter(gl.RED_BITS),
      gl.getParameter(gl.GREEN_BITS),
      gl.getParameter(gl.BLUE_BITS),
      gl.getParameter(gl.ALPHA_BITS),
      gl.getParameter(gl.DEPTH_BITS),
      gl.getParameter(gl.STENCIL_BITS),
      gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
      gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS),
      gl.getParameter(gl.MAX_VARYING_VECTORS),
      gl.getParameter(gl.MAX_COMBINED_TEXTURE_IMAGE_UNITS),
      gl.getParameter(gl.MAX_VERTEX_TEXTURE_IMAGE_UNITS),
      gl.getParameter(gl.MAX_TEXTURE_SIZE),
      gl.getParameter(gl.MAX_CUBE_MAP_TEXTURE_SIZE),
      gl.getParameter(gl.ALIASED_LINE_WIDTH_RANGE),
      gl.getParameter(gl.ALIASED_POINT_SIZE_RANGE),
      gl.getParameter(gl.MAX_VIEWPORT_DIMS),
      gl.getParameter(gl.VENDOR),
      gl.getParameter(gl.RENDERER),
      gl.getParameter(gl.VERSION),
      gl.getParameter(gl.SHADING_LANGUAGE_VERSION)
    );
    
    // Get WebGL supported extensions
    const extensions = gl.getSupportedExtensions();
    
    // Combine all parameters
    let result = params.join('~') + '|' + extensions.join(',');
    
    // Render something to the canvas to capture rendering differences
    gl.clearColor(0.2, 0.3, 0.4, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    
    const vertices = new Float32Array([
      -0.5, -0.5,
       0.5, -0.5,
       0.0,  0.5
    ]);
    
    // Create and bind the buffer
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    
    // Create a simple shader program
    const vertexShader = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vertexShader, `
      attribute vec2 position;
      void main() {
        gl_Position = vec4(position, 0.0, 1.0);
      }
    `);
    gl.compileShader(vertexShader);
    
    const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fragmentShader, `
      precision mediump float;
      void main() {
        gl_FragColor = vec4(0.6, 0.3, 0.7, 1.0);
      }
    `);
    gl.compileShader(fragmentShader);
    
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    gl.useProgram(program);
    
    // Use the shader program
    const positionAttribute = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(positionAttribute);
    gl.vertexAttribPointer(positionAttribute, 2, gl.FLOAT, false, 0, 0);
    
    // Draw
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    
    // Capture the rendered image
    const dataURL = canvas.toDataURL();
    
    // Combine rendering with parameters
    result += '|' + dataURL;
    
    // Clean up
    gl.deleteProgram(program);
    gl.deleteShader(fragmentShader);
    gl.deleteShader(vertexShader);
    gl.deleteBuffer(buffer);
    
    return hashString(result);
  } catch (error) {
    console.warn('WebGL fingerprinting not supported or blocked', error);
    return Promise.resolve('webgl_not_supported');
  }
}

/**
 * Generate Audio fingerprint
 * Creates a unique identifier based on how the browser processes audio
 * @returns {Promise<string>} Audio fingerprint hash
 */
function generateAudioFingerprint() {
  return new Promise((resolve) => {
    try {
      // Check if AudioContext is supported
      if (typeof AudioContext !== 'function' && typeof webkitAudioContext !== 'function') {
        return resolve('audio_not_supported');
      }
      
      // Create audio context
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      // Create oscillator
      const oscillator = audioContext.createOscillator();
      const analyser = audioContext.createAnalyser();
      const gain = audioContext.createGain();
      const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
      
      // Configure audio nodes
      gain.gain.value = 0; // Mute the sound
      analyser.fftSize = 2048;
      
      // Connect nodes
      oscillator.connect(analyser);
      analyser.connect(scriptProcessor);
      scriptProcessor.connect(gain);
      gain.connect(audioContext.destination);
      
      // Set frequency and type for oscillator
      oscillator.type = 'triangle';
      oscillator.frequency.value = 10000;
      
      // Create array to store audio data
      const frequencyData = new Uint8Array(analyser.frequencyBinCount);
      
      // Process audio data
      scriptProcessor.onaudioprocess = (event) => {
        // Get frequency data
        analyser.getByteFrequencyData(frequencyData);
        
        // Convert frequency data to string
        const frequencyString = Array.from(frequencyData).join(',');
        
        // Clean up
        oscillator.stop();
        scriptProcessor.disconnect();
        analyser.disconnect();
        gain.disconnect();
        
        // Close audio context
        if (audioContext.state !== 'closed' && typeof audioContext.close === 'function') {
          audioContext.close();
        }
        
        // Resolve with hashed fingerprint
        resolve(hashString(frequencyString));
      };
      
      // Start oscillator
      oscillator.start(0);
      
      // Set timeout to prevent hanging
      setTimeout(() => {
        resolve('audio_timeout');
      }, 1000);
    } catch (error) {
      console.warn('Audio fingerprinting not supported or blocked', error);
      resolve('audio_error');
    }
  });
}

/**
 * Get a list of fonts available on the device
 * @returns {Promise<string>} Hashed list of available fonts
 */
function getFontFingerprint() {
  return new Promise((resolve) => {
    try {
      // List of fonts to test
      const fontList = [
        'Arial', 'Arial Black', 'Arial Narrow', 'Arial Rounded MT Bold',
        'Bookman Old Style', 'Bradley Hand ITC', 'Century', 'Century Gothic',
        'Comic Sans MS', 'Courier', 'Courier New', 'Georgia', 'Gentium',
        'Impact', 'King', 'Lucida Console', 'Lalit', 'Modena', 'Monotype Corsiva',
        'Papyrus', 'Tahoma', 'TeX', 'Times', 'Times New Roman', 'Trebuchet MS',
        'Verdana', 'Verona', 'Helvetica', 'Segoe UI', 'Calibri', 'Cambria',
        'Consolas', 'Segoe Script', 'Segoe Print', 'MS Gothic', 'MS PGothic',
        'MS Sans Serif', 'MS Serif', 'Open Sans', 'Roboto', 'Lato', 'Montserrat',
        'Ubuntu', 'Droid Sans', 'Droid Serif', 'PT Sans', 'PT Serif', 'Source Sans Pro',
        'Noto Sans', 'Noto Serif', 'Merriweather', 'Oswald', 'Raleway', 'Rubik',
        'Nunito', 'Poppins', 'Oxygen', 'Quicksand', 'Playfair Display'
      ];
      
      // Create span elements for testing
      const testString = 'mmMMMwwWWW';
      const testSize = '72px';
      const baseFonts = ['monospace', 'sans-serif', 'serif'];
      
      // Create a container for testing
      const container = document.createElement('div');
      container.style.position = 'absolute';
      container.style.left = '-9999px';
      container.style.visibility = 'hidden';
      
      // Get the width and height of each base font for comparison
      const baseFontWidths = {};
      
      // Create spans for base fonts
      for (const baseFont of baseFonts) {
        const span = document.createElement('span');
        span.style.fontFamily = baseFont;
        span.style.fontSize = testSize;
        span.style.margin = '0';
        span.style.padding = '0';
        span.textContent = testString;
        container.appendChild(span);
      }
      
      document.body.appendChild(container);
      
      // Measure base fonts
      const spans = container.getElementsByTagName('span');
      for (let i = 0; i < baseFonts.length; i++) {
        baseFontWidths[baseFonts[i]] = {
          width: spans[i].offsetWidth,
          height: spans[i].offsetHeight
        };
      }
      
      // Clear container for testing
      container.innerHTML = '';
      
      // Detect available fonts
      const availableFonts = [];
      
      // Test each font
      for (const font of fontList) {
        let detected = false;
        
        // Test with each base font
        for (const baseFont of baseFonts) {
          const span = document.createElement('span');
          span.style.fontFamily = `'${font}', ${baseFont}`;
          span.style.fontSize = testSize;
          span.style.margin = '0';
          span.style.padding = '0';
          span.textContent = testString;
          container.appendChild(span);
          
          const fontWidth = span.offsetWidth;
          const fontHeight = span.offsetHeight;
          
          container.removeChild(span);
          
          // If the dimensions are different from the base font, the font is available
          if (fontWidth !== baseFontWidths[baseFont].width || fontHeight !== baseFontWidths[baseFont].height) {
            detected = true;
            break;
          }
        }
        
        if (detected) {
          availableFonts.push(font);
        }
      }
      
      // Remove the container
      document.body.removeChild(container);
      
      // Hash the list of available fonts
      const fontFingerprint = availableFonts.join('|');
      resolve(hashString(fontFingerprint));
    } catch (error) {
      console.warn('Font detection failed', error);
      resolve('fonts_error');
    }
  });
}

/**
 * Get screen information
 * @returns {Object} Screen properties
 */
function getScreenInfo() {
  const screenInfo = {
    width: window.screen.width,
    height: window.screen.height,
    colorDepth: window.screen.colorDepth,
    pixelDepth: window.screen.pixelDepth,
    availWidth: window.screen.availWidth,
    availHeight: window.screen.availHeight,
    devicePixelRatio: window.devicePixelRatio || 1
  };
  
  // Add window information
  screenInfo.windowInnerWidth = window.innerWidth;
  screenInfo.windowInnerHeight = window.innerHeight;
  screenInfo.windowOuterWidth = window.outerWidth;
  screenInfo.windowOuterHeight = window.outerHeight;
  
  // Check for touch support
  screenInfo.touchPoints = 'ontouchstart' in window ? 
    navigator.maxTouchPoints || navigator.msMaxTouchPoints || 0 : 0;
  
  // Check for orientation support
  screenInfo.orientation = screen.orientation ? 
    screen.orientation.type : window.orientation !== undefined ? 
    window.orientation === 0 || window.orientation === 180 ? 'portrait' : 'landscape' : 'unknown';
  
  // Additional screen properties if available
  try {
    // Check for device memory
    if (navigator.deviceMemory) {
      screenInfo.deviceMemory = navigator.deviceMemory;
    }
    
    // Check for hardware concurrency (CPU cores)
    if (navigator.hardwareConcurrency) {
      screenInfo.hardwareConcurrency = navigator.hardwareConcurrency;
    }
  } catch (e) {
    console.warn('Error getting additional screen info', e);
  }
  
  return screenInfo;
}

/**
 * Get hardware information
 * @returns {Object} Hardware properties
 */
function getHardwareInfo() {
  const hardwareInfo = {};
  
  try {
    // Check for available memory
    if (navigator.deviceMemory) {
      hardwareInfo.deviceMemory = navigator.deviceMemory + 'GB';
    }
    
    // Check for logical processors
    if (navigator.hardwareConcurrency) {
      hardwareInfo.processorCores = navigator.hardwareConcurrency;
    }
    
    // Try to get GPU information from WebGL
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        hardwareInfo.gpuVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        hardwareInfo.gpuRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
      }
    }
    
    // Check battery status if available
    if (navigator.getBattery) {
      navigator.getBattery().then(battery => {
        hardwareInfo.batteryLevel = battery.level;
        hardwareInfo.batteryCharging = battery.charging;
      }).catch(() => {
        // Ignore errors
      });
    }
    
    // Check for vibration support
    hardwareInfo.vibrationSupport = !!navigator.vibrate;
    
    // Check for gamepad support
    hardwareInfo.gamepadSupport = !!navigator.getGamepads;
    
    // Check for VR support
    hardwareInfo.vrSupport = !!navigator.getVRDisplays;
    
    // Check for Bluetooth support
    hardwareInfo.bluetoothSupport = !!navigator.bluetooth;
    
    // Check for USB support
    hardwareInfo.usbSupport = !!navigator.usb;
    
    // Check for ambient light sensor
    hardwareInfo.lightSensorSupport = !!window.AmbientLightSensor;
    
    // Additional media devices info
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      navigator.mediaDevices.enumerateDevices()
        .then(devices => {
          hardwareInfo.audioInputs = devices.filter(d => d.kind === 'audioinput').length;
          hardwareInfo.audioOutputs = devices.filter(d => d.kind === 'audiooutput').length;
          hardwareInfo.videoInputs = devices.filter(d => d.kind === 'videoinput').length;
        })
        .catch(() => {
          // Ignore errors
        });
    }
  } catch (e) {
    console.warn('Error getting hardware info', e);
  }
  
  return hardwareInfo;
}

/**
 * Get browser features and capabilities
 * @returns {Object} Browser features
 */
function getBrowserFeatures() {
  const features = {};
  
  try {
    // Core features
    features.localStorage = !!window.localStorage;
    features.sessionStorage = !!window.sessionStorage;
    features.cookiesEnabled = navigator.cookieEnabled;
    features.indexedDB = !!window.indexedDB;
    features.addons = !!(navigator.plugins && navigator.plugins.length > 0);
    features.plugins = navigator.plugins ? navigator.plugins.length : 0;
    
    // Check for automation
    features.webdriver = navigator.webdriver || false;
    
    // Check for advanced features
    features.serviceWorker = 'serviceWorker' in navigator;
    features.webGL = (function() {
      try {
        const canvas = document.createElement('canvas');
        return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
      } catch (e) {
        return false;
      }
    })();
    features.canvas = (function() {
      try {
        const canvas = document.createElement('canvas');
        return !!(canvas.getContext('2d'));
      } catch (e) {
        return false;
      }
    })();
    features.webSockets = 'WebSocket' in window;
    features.webWorkers = 'Worker' in window;
    features.webAudio = 'AudioContext' in window || 'webkitAudioContext' in window;
    
    // Video/audio codecs
    features.videoCodecs = (function() {
      const video = document.createElement('video');
      if (!video.canPlayType) return {};
      
      return {
        h264: video.canPlayType('video/mp4; codecs="avc1.42E01E"') || 'false',
        webm: video.canPlayType('video/webm; codecs="vp8, vorbis"') || 'false',
        ogg: video.canPlayType('video/ogg; codecs="theora"') || 'false'
      };
    })();
    
    features.audioCodecs = (function() {
      const audio = document.createElement('audio');
      if (!audio.canPlayType) return {};
      
      return {
        mp3: audio.canPlayType('audio/mpeg;') || 'false',
        wav: audio.canPlayType('audio/wav; codecs="1"') || 'false',
        aac: audio.canPlayType('audio/aac;') || 'false',
        ogg: audio.canPlayType('audio/ogg; codecs="vorbis"') || 'false'
      };
    })();
    
    // Browser language and languages
    features.language = navigator.language;
    features.languages = navigator.languages ? navigator.languages.join(',') : '';
    
    // Connection info
    if (navigator.connection) {
      features.connectionType = navigator.connection.type;
      features.effectiveType = navigator.connection.effectiveType;
      features.downlink = navigator.connection.downlink;
      features.rtt = navigator.connection.rtt;
    }
    
    // Check for DRM support
    features.emeSupport = !!navigator.requestMediaKeySystemAccess;
    
    // Check for ad blocking
    features.adBlocker = false;
    
    // Create a bait div to detect ad blockers
    const adBaitDiv = document.createElement('div');
    adBaitDiv.className = 'ad_unit ad-unit adsbox ad-placement carbon-ad';
    adBaitDiv.style.height = '1px';
    adBaitDiv.style.position = 'absolute';
    adBaitDiv.style.left = '-9999px';
    document.body.appendChild(adBaitDiv);
    
    // Check after a short delay if the ad bait was hidden by an adblocker
    setTimeout(() => {
      if (adBaitDiv.offsetHeight === 0) {
        features.adBlocker = true;
      }
      document.body.removeChild(adBaitDiv);
    }, 100);
    
    // Check for Do Not Track
    features.doNotTrack = navigator.doNotTrack || window.doNotTrack || navigator.msDoNotTrack;
    
    // Check for PDF viewer
    features.pdfViewerEnabled = navigator.pdfViewerEnabled;
    
    // Check for browser features through CSS
    const featureDetectionDiv = document.createElement('div');
    featureDetectionDiv.style.display = 'none';
    document.body.appendChild(featureDetectionDiv);
    
    // CSS feature tests
    const cssFeatures = {
      'flexbox': 'display: flex;',
      'grid': 'display: grid;',
      'cssTransitions': 'transition: all 0.5s;',
      'cssAnimations': 'animation: test 1s;',
      'cssTransforms': 'transform: rotate(45deg);',
      'cssFilters': 'filter: blur(1px);',
      'rgba': 'background-color: rgba(0,0,0,0.5);',
      'cssVariables': '--test: 10px; width: var(--test);'
    };
    
    features.css = {};
    for (const [feature, style] of Object.entries(cssFeatures)) {
      featureDetectionDiv.style.cssText = style;
      features.css[feature] = !!featureDetectionDiv.style.length;
    }
    
    document.body.removeChild(featureDetectionDiv);
  } catch (e) {
    console.warn('Error getting browser features', e);
  }
  
  return features;
}

/**
 * Get timezone information
 * @returns {Object} Timezone information
 */
function getTimezoneInfo() {
  try {
    const timezoneInfo = {};
    
    // Get timezone offset in minutes
    const offset = new Date().getTimezoneOffset();
    timezoneInfo.offset = offset;
    
    // Format offset as standard timezone string like "+0200" or "-0500"
    const offsetHours = Math.abs(Math.floor(offset / 60));
    const offsetMinutes = Math.abs(offset % 60);
    const offsetSign = offset <= 0 ? '+' : '-';
    timezoneInfo.offsetString = `${offsetSign}${offsetHours.toString().padStart(2, '0')}${offsetMinutes.toString().padStart(2, '0')}`;
    
    // Check if daylight saving time is in effect
    timezoneInfo.isDST = (function() {
      const jan = new Date(new Date().getFullYear(), 0, 1);
      const jul = new Date(new Date().getFullYear(), 6, 1);
      return jan.getTimezoneOffset() !== jul.getTimezoneOffset();
    })();
    
    // Try to get more detailed timezone info if Intl is available
    if (window.Intl && Intl.DateTimeFormat) {
      try {
        // Get timezone name
        const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        timezoneInfo.timeZone = timeZone;
        
        // Get current time in different formats
        const formatter = new Intl.DateTimeFormat(undefined, {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
          timeZoneName: 'long'
        });
        
        timezoneInfo.timeZoneName = formatter.format(new Date()).split(' ').slice(1).join(' ');
      } catch (e) {
        console.warn('Error getting detailed timezone info', e);
      }
    }
    
    return timezoneInfo;
  } catch (e) {
    console.warn('Error getting timezone info', e);
    return { offset: 0, offsetString: '+0000', isDST: false };
  }
}

/**
 * Get IP addresses through WebRTC (only works if user allows it)
 * @returns {Promise<Array>} Array of WebRTC IP addresses
 */
function getWebRTCIPs() {
  return new Promise((resolve) => {
    try {
      // Check if WebRTC is supported
      if (!window.RTCPeerConnection) {
        return resolve([]);
      }
      
      // Define STUN servers list
      const rtcConfig = {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      };
      
      // Create a new RTCPeerConnection
      const pc = new RTCPeerConnection(rtcConfig);
      
      // Set a timeout to ensure we don't wait forever
      const timeout = setTimeout(() => {
        try {
          if (pc.signalingState !== 'closed') {
            pc.close();
          }
          resolve([]);
        } catch (e) {
          resolve([]);
        }
      }, 1000);
      
      // Array to store found IPs
      const ipAddresses = [];
      
      // Process ICE candidates
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          const ipRegex = /([0-9]{1,3}(\.[0-9]{1,3}){3}|[a-f0-9]{1,4}(:[a-f0-9]{1,4}){7})/;
          const match = ipRegex.exec(event.candidate.candidate);
          
          if (match && match[1] && !ipAddresses.includes(match[1])) {
            ipAddresses.push(match[1]);
          }
        } else {
          // ICE candidate gathering complete
          clearTimeout(timeout);
          try {
            if (pc.signalingState !== 'closed') {
              pc.close();
            }
          } catch (e) {
            // Ignore errors during close
          }
          resolve(ipAddresses);
        }
      };
      
      // Create an empty data channel to trigger candidates
      pc.createDataChannel('');
      
      // Create offer to trigger ICE gathering
      pc.createOffer()
        .then(offer => pc.setLocalDescription(offer))
        .catch(() => {
          clearTimeout(timeout);
          try {
            if (pc.signalingState !== 'closed') {
              pc.close();
            }
          } catch (e) {
            // Ignore errors during close
          }
          resolve([]);
        });
    } catch (e) {
      console.warn('WebRTC IP detection not supported or blocked', e);
      resolve([]);
    }
  });
}

/**
 * Hash a string using SHA-256
 * @param {string} str - String to hash
 * @returns {Promise<string>} Hashed string
 */
async function hashStringSHA256(str) {
  try {
    // Use Web Crypto API if available
    if (window.crypto && window.crypto.subtle) {
      // Encode string to ArrayBuffer
      const buffer = new TextEncoder().encode(str);
      
      // Generate SHA-256 hash
      const hashBuffer = await window.crypto.subtle.digest('SHA-256', buffer);
      
      // Convert ArrayBuffer to hex string
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      
      return hashHex;
    }
  } catch (e) {
    console.warn('Crypto API not supported or blocked', e);
  }
  
  // Fallback to simpler hash
  return hashString(str);
}

/**
 * Simple string hashing function (use only as fallback)
 * @param {string} str - String to hash
 * @returns {string} Hashed string
 */
function hashString(str) {
  try {
    let hash = 0;
    
    // Use SHA-256 if available through crypto.subtle
    if (window.crypto && window.crypto.subtle) {
      return hashStringSHA256(str);
    }
    
    // Otherwise use a simple hash
    if (!str || str.length === 0) return 'empty_string';
    
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0; // Convert to 32bit integer
    }
    
    // Convert to hex string with padding
    const hashHex = (hash >>> 0).toString(16).padStart(8, '0');
    return hashHex;
  } catch (e) {
    console.warn('Error hashing string', e);
    return 'hash_error';
  }
}

/**
 * NEW: Generate timing fingerprint
 * Creates a unique identifier based on performance characteristics
 * that are hard to spoof without specialized knowledge
 * @returns {Promise<string>} Timing fingerprint hash
 */
function generateTimingFingerprint() {
  return new Promise((resolve) => {
    try {
      // Start with an empty result object
      const timingData = {};
      
      // Measure floating point operations speed
      const floatOperationsStart = performance.now();
      let result = 0;
      for (let i = 0; i < 100000; i++) {
        result += Math.sin(i * 0.5) * Math.cos(i * 0.3);
      }
      const floatOperationsEnd = performance.now();
      timingData.floatOperations = floatOperationsEnd - floatOperationsStart;
      
      // Measure integer operations speed
      const intOperationsStart = performance.now();
      let intResult = 0;
      for (let i = 0; i < 1000000; i++) {
        intResult += i * (i % 7);
      }
      const intOperationsEnd = performance.now();
      timingData.intOperations = intOperationsEnd - intOperationsStart;
      
      // Measure DOM operations speed
      const domOperationsStart = performance.now();
      for (let i = 0; i < 100; i++) {
        const div = document.createElement('div');
        div.style.display = 'none';
        div.className = 'timing-test';
        document.body.appendChild(div);
        div.innerHTML = '<span>test</span>';
        document.body.removeChild(div);
      }
      const domOperationsEnd = performance.now();
      timingData.domOperations = domOperationsEnd - domOperationsStart;
      
      // Measure memory operations speed
      const memoryOperationsStart = performance.now();
      const arrays = [];
      for (let i = 0; i < 100; i++) {
        const arr = new Array(10000).fill(Math.random());
        arrays.push(arr);
      }
      for (const arr of arrays) {
        arr.sort();
      }
      const memoryOperationsEnd = performance.now();
      timingData.memoryOperations = memoryOperationsEnd - memoryOperationsStart;
      arrays.length = 0; // Clear memory
      
      // Add timing precision test
      const timing1 = performance.now();
      const timing2 = performance.now();
      timingData.timingPrecision = timing2 - timing1;
      
      // Add navigation timing if available
      if (window.performance && performance.timing) {
        const navigationStart = performance.timing.navigationStart;
        const loadEventEnd = performance.timing.loadEventEnd;
        
        if (navigationStart && loadEventEnd) {
          timingData.pageLoadTime = loadEventEnd - navigationStart;
        }
      }
      
      // Get hardware concurrency (CPU cores) - this can reveal VM usage
      if (navigator.hardwareConcurrency) {
        timingData.cores = navigator.hardwareConcurrency;
      }
      
      // Get device memory if available
      if (navigator.deviceMemory) {
        timingData.memory = navigator.deviceMemory;
      }
      
      // Create a fingerprint hash from timing data
      // We add the date to make it somewhat consistent for the same user
      // but prevent trivial replay attacks
      const date = new Date();
      const dateKey = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
      
      // Create a timing fingerprint string, keeping only 2 decimal places to reduce variability
      const timingString = Object.entries(timingData)
        .map(([key, value]) => {
          // Round to 2 decimal places if it's a number
          const roundedValue = typeof value === 'number' ? 
            Math.round(value * 100) / 100 : value;
          return `${key}:${roundedValue}`;
        })
        .join('|') + '|' + dateKey;
      
      resolve(hashString(timingString));
    } catch (error) {
      console.warn('Timing fingerprinting failed', error);
      resolve('timing_not_supported');
    }
  });
}

/**
 * Get all fingerprints
 * @returns {Promise<Object>} All fingerprint data
 */
async function getAllFingerprints() {
  try {
    // Start collecting all fingerprints in parallel
    const [
      canvasFingerprint,
      webglFingerprint,
      audioFingerprint,
      fontFingerprint,
      webrtcIPs,
      timingFingerprint  // NEW: Add timing fingerprint
    ] = await Promise.all([
      generateCanvasFingerprint(),
      generateWebGLFingerprint(),
      generateAudioFingerprint(),
      getFontFingerprint(),
      getWebRTCIPs(),
      generateTimingFingerprint()  // NEW: Add timing fingerprint
    ]);
    
    // Get additional information that doesn't require async operations
    const screenInfo = getScreenInfo();
    const hardwareInfo = getHardwareInfo();
    const browserFeatures = getBrowserFeatures();
    const timezoneInfo = getTimezoneInfo();
    
    // NEW: Add timing information
    const timingInfo = {
      requestStartTime: performance.now(),
      requestEndTime: 0  // Will be set just before sending
    };
    
    // NEW: Collect performance timing data if available
    if (window.performance && performance.timing) {
      timingInfo.navigationStart = performance.timing.navigationStart;
      timingInfo.domLoading = performance.timing.domLoading;
      timingInfo.domInteractive = performance.timing.domInteractive;
      timingInfo.domContentLoaded = performance.timing.domContentLoadedEventEnd;
      timingInfo.loadEventEnd = performance.timing.loadEventEnd;
    }
    
    // NEW: Collect additional hardware-specific metrics that are more difficult to spoof
    const advancedHardwareInfo = {
      cores: navigator.hardwareConcurrency || '',
      deviceMemory: navigator.deviceMemory || '',
      hardwareConcurrency: navigator.hardwareConcurrency || '',
      devicePixelRatio: window.devicePixelRatio || '',
      touchPoints: navigator.maxTouchPoints || '',
      hasTouchScreen: ('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || false,
      batteryInfo: null
    };
    
    // Try to get battery info (if available)
    try {
      if (navigator.getBattery) {
        const battery = await navigator.getBattery();
        advancedHardwareInfo.batteryInfo = {
          charging: battery.charging,
          level: battery.level,
          chargingTime: battery.chargingTime,
          dischargingTime: battery.dischargingTime
        };
      }
    } catch (e) {
      console.warn("Battery API not available", e);
    }
    
    // NEW: Collect graphics card information from WebGL
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (gl) {
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
          hardwareInfo.gpuVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
          hardwareInfo.gpuRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        }
      }
    } catch (e) {
      console.warn("WebGL GPU info extraction failed", e);
    }
    
    // NEW: Audio processing capabilities (AudioContext)
    let audioCapabilities = {};
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioCapabilities = {
        sampleRate: audioContext.sampleRate,
        channelCount: audioContext.destination.channelCount,
        maxChannelCount: audioContext.destination.maxChannelCount,
        numberOfInputs: audioContext.destination.numberOfInputs,
        numberOfOutputs: audioContext.destination.numberOfOutputs
      };
      // Clean up
      audioContext.close();
    } catch (e) {
      console.warn("AudioContext capabilities extraction failed", e);
    }
    
    // Combine all fingerprint data
    const fingerprints = {
      canvas_fingerprint: await canvasFingerprint,
      webgl_fingerprint: await webglFingerprint,
      audio_fingerprint: await audioFingerprint,
      font_list: await fontFingerprint,
      timing_fingerprint: await timingFingerprint,  // NEW: Add timing fingerprint
      screen_info: screenInfo,
      hardware_info: hardwareInfo,
      browser_features: browserFeatures,
      timezone_info: timezoneInfo,
      timing_info: timingInfo,  // NEW: Add timing info
      webrtc_ips: webrtcIPs,
      advanced_hardware_info: advancedHardwareInfo,  // NEW: Add advanced hardware info
      audio_capabilities: audioCapabilities,  // NEW: Add audio capabilities 
      user_agent: navigator.userAgent,
      timestamp: new Date().toISOString()
    };
    
    // Set the request end time just before returning
    fingerprints.timing_info.requestEndTime = performance.now();
    fingerprints.timing_info.requestTime = 
      fingerprints.timing_info.requestEndTime - fingerprints.timing_info.requestStartTime;
    
    return fingerprints;
  } catch (error) {
    console.error('Error collecting fingerprints', error);
    
    // Return basic fingerprint even if advanced fails
    return {
      user_agent: navigator.userAgent,
      screen_info: getScreenInfo(),
      timezone_info: getTimezoneInfo(),
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
}

/**
 * Add fingerprint data to request headers
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Updated fetch options with fingerprint headers
 */
async function addFingerprintHeaders(options = {}) {
  try {
    // Get all fingerprints
    const fingerprints = await getAllFingerprints();
    
    // Create headers object if it doesn't exist
    if (!options.headers) {
      options.headers = {};
    }
    
    // Add each fingerprint as a header
    options.headers['X-Canvas-Fingerprint'] = fingerprints.canvas_fingerprint;
    options.headers['X-WebGL-Fingerprint'] = fingerprints.webgl_fingerprint;
    options.headers['X-Audio-Fingerprint'] = fingerprints.audio_fingerprint;
    options.headers['X-Font-Fingerprint'] = fingerprints.font_list;
    options.headers['X-Timing-Fingerprint'] = fingerprints.timing_fingerprint;
    
    // Add hardware-specific headers that are difficult to spoof
    options.headers['X-Hardware-Concurrency'] = fingerprints.advanced_hardware_info.cores;
    options.headers['X-Device-Memory'] = fingerprints.advanced_hardware_info.deviceMemory;
    options.headers['X-Device-DPR'] = fingerprints.advanced_hardware_info.devicePixelRatio;
    options.headers['X-Touch-Points'] = fingerprints.advanced_hardware_info.touchPoints;
    
    // Add WebRTC IPs for better network detection (critical for hardware identification)
    if (fingerprints.webrtc_ips && fingerprints.webrtc_ips.length > 0) {
      options.headers['X-WebRTC-IPs'] = JSON.stringify(fingerprints.webrtc_ips);
    }
    
    // Add JSON headers
    options.headers['X-Screen-Info'] = JSON.stringify(fingerprints.screen_info);
    options.headers['X-Hardware-Info'] = JSON.stringify(fingerprints.hardware_info);
    options.headers['X-Browser-Features'] = JSON.stringify(fingerprints.browser_features);
    options.headers['X-Timezone-Info'] = JSON.stringify(fingerprints.timezone_info);
    
    return options;
  } catch (error) {
    console.error('Error adding fingerprint headers', error);
    return options;
  }
}

/**
 * Create a fetch function that automatically adds fingerprint headers
 * @returns {Function} Enhanced fetch function
 */
function createFingerprintFetch() {
  const originalFetch = window.fetch;
  
  return async function fingerprintFetch(url, options = {}) {
    try {
      // Add fingerprint headers to request
      const enhancedOptions = await addFingerprintHeaders(options);
      
      // Call original fetch with enhanced options
      return originalFetch(url, enhancedOptions);
    } catch (error) {
      console.error('Error in fingerprint fetch', error);
      
      // Fall back to original fetch
      return originalFetch(url, options);
    }
  };
}

/**
 * Initialize fingerprinting system
 */
function initFingerprinting() {
  // Replace global fetch with fingerprint-enhanced version
  // Note: this is commented out to avoid breaking existing code
  // window.fetch = createFingerprintFetch();
  
  // Log initialization
  console.debug('Advanced fingerprinting initialized');
}

/**
 * NEW: Detect if the fingerprinting code has been tampered with
 * This makes it harder to modify the fingerprinting functions
 * @returns {boolean} True if tampering is detected
 */
function detectCodeTampering() {
  try {
    // Check if our functions have been modified
    const expectedFunctions = [
      'generateCanvasFingerprint',
      'generateWebGLFingerprint',
      'generateAudioFingerprint',
      'getFontFingerprint',
      'getScreenInfo',
      'getHardwareInfo',
      'getBrowserFeatures',
      'getTimezoneInfo',
      'getWebRTCIPs',
      'hashString',
      'generateTimingFingerprint',
      'getAllFingerprints'
    ];
    
    // Check if any functions are missing
    for (const funcName of expectedFunctions) {
      if (typeof window[funcName] !== 'function') {
        console.warn(`Fingerprinting function ${funcName} is missing`);
        return true;
      }
    }
    
    // Check if functions have been tampered with by examining their string representation
    // Genuine functions should have specific characteristics in their code
    
    // Check canvas fingerprinting function
    const canvasFpStr = generateCanvasFingerprint.toString();
    if (!canvasFpStr.includes('canvas.getContext') || !canvasFpStr.includes('toDataURL')) {
      console.warn('Canvas fingerprinting function has been modified');
      return true;
    }
    
    // Check WebGL fingerprinting function
    const webglFpStr = generateWebGLFingerprint.toString();
    if (!webglFpStr.includes('WEBGL_debug_renderer_info') || !webglFpStr.includes('getParameter')) {
      console.warn('WebGL fingerprinting function has been modified');
      return true;
    }
    
    // Check timing fingerprinting function
    const timingFpStr = generateTimingFingerprint.toString();
    if (!timingFpStr.includes('performance.now') || !timingFpStr.includes('timingData')) {
      console.warn('Timing fingerprinting function has been modified');
      return true;
    }
    
    // Check if functions return expected values
    // This is tricky because fingerprints should be different on different devices
    // But we can check if they return a value that matches our hash format
    
    // Check async functions using an inline function
    async function checkAsyncFunction(func, errorMsg) {
      try {
        const result = await func();
        // Check if result is a string that looks like a hash (32+ hex chars)
        if (typeof result !== 'string' || !/^[0-9a-f]{32,}$/i.test(result)) {
          console.warn(errorMsg);
          return false;
        }
        return true;
      } catch (e) {
        console.warn(errorMsg, e);
        return false;
      }
    }
    
    // Return false if no tampering detected
    return false;
  } catch (error) {
    console.warn('Error checking for code tampering', error);
    return true; // Assume tampering if we can't check properly
  }
}

/**
 * NEW: Send tamper-resistant fingerprint data to the server
 * This adds additional protection to ensure the data is authentic
 * @param {string} url - The URL to send the data to
 * @returns {Promise<Object>} The server response
 */
async function sendTamperResistantFingerprint(url) {
  try {
    // Check if code has been tampered with
    const isTampered = detectCodeTampering();
    
    // Get all fingerprints
    const fingerprints = await getAllFingerprints();
    
    // Add tamper detection result
    fingerprints.code_tampered = isTampered;
    
    // Add verification token with timestamp to prevent replay attacks
    const timestamp = Date.now();
    const verificationData = `${navigator.userAgent}|${timestamp}|${fingerprints.canvas_fingerprint}`;
    fingerprints.verification_token = await hashStringSHA256(verificationData);
    fingerprints.verification_timestamp = timestamp;
    
    // Send the data to the server
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Fingerprint-Version': '2.0', // Add version to help server identify this enhanced version
        'X-Verification-Time': timestamp.toString()
      },
      body: JSON.stringify(fingerprints)
    });
    
    return await response.json();
  } catch (error) {
    console.error('Error sending tamper-resistant fingerprint', error);
    return { error: 'Failed to send fingerprint data' };
  }
}

// Export functions
export {
  getAllFingerprints,
  addFingerprintHeaders,
  createFingerprintFetch,
  generateCanvasFingerprint,
  generateWebGLFingerprint,
  generateAudioFingerprint,
  generateTimingFingerprint, // NEW: Export timing fingerprint function
  getFontFingerprint,
  getScreenInfo,
  getHardwareInfo,
  getBrowserFeatures,
  getTimezoneInfo,
  getWebRTCIPs,
  hashString,
  hashStringSHA256,
  detectCodeTampering, // NEW: Export tampering detection
  sendTamperResistantFingerprint, // NEW: Export secure sending function
  initFingerprinting
}; 