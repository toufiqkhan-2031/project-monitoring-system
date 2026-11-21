window.onload = function () {

  // Splash animation (only runs on index/welcome page)
  const gyro = document.getElementById("gyro");
  const welcome = document.getElementById("welcome");
  const startBtn = document.getElementById("startBtn");

  if (gyro) gyro.style.opacity = 1;

  setTimeout(() => {
    if (welcome) welcome.style.opacity = 1;
  }, 1000);

  setTimeout(() => {
    if (startBtn) startBtn.style.opacity = 1;
  }, 2000);

  // CAPTCHA — only generate if the captcha element exists on this page
  const captchaEl = document.getElementById("captcha-question");
  if (captchaEl) {
    generatecaptcha();
  }

};

// ── CAPTCHA ──
let x, y;

function generatecaptcha() {
  const captchaEl = document.getElementById("captcha-question");
  if (!captchaEl) return; // safety check — exit if not on login page

  x = Math.floor(Math.random() * 10) + 1;
  y = Math.floor(Math.random() * 10) + 1;
  captchaEl.innerText = "What is " + x + " + " + y + "?";
}

document.addEventListener("DOMContentLoaded", function () {
  const captchaEl = document.getElementById("captcha-question");
  if (captchaEl) {
    generatecaptcha();
  }
});

function validatecaptcha() {
  const inputEl = document.getElementById("captcha-input");
  if (!inputEl) return true; // if no captcha on page, allow submit

  let userAns = inputEl.value;

  if (parseInt(userAns) === x + y) {
    return true;
  } else {
    alert("Wrong captcha!");
    generatecaptcha();
    return false;
  }
}