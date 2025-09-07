const tg = window.Telegram.WebApp;
tg.expand();

// ✅ ADD THIS LINE
const BACKEND_URL = "https://quizzy-tg-mini-app-backend.onrender.com"; // ← NO TRAILING SPACE!
let userId = tg.initDataUnsafe?.user?.id || 5138176448; // ← Your Telegram ID
let sessionId = null;
let currentStep = 1;
let starBalance = 0;

// Questions
const questions = [
  {
    text: "When you get $100, you:",
    options: ["🚀 Invest it", "🛍️ Spend it", "💰 Save it", "🎁 Gift it"],
  },
  {
    text: "Your dream 2025 life:",
    options: [
      "🌴 Beach + passive income",
      "🏦 Quiet millionaire",
      "🌍 Digital nomad",
      "🎮 Gaming & crypto",
    ],
  },
  {
    text: "Your money spirit animal:",
    options: ["🐋 Whale", "🐺 Wolf", "🦊 Fox", "🐢 Tortoise"],
  },
];

// Initialize
async function init() {
  if (!userId) {
    alert("Please open this app inside Telegram!");
    return;
  }

  // ✅ FIXED: Use BACKEND_URL
  const user = await fetch(
    `${BACKEND_URL}/api/user?telegram_id=${userId}`
  ).then((r) => r.json());
  starBalance = user.virtual_stars || 0;
  document.getElementById("starBalance").innerText = starBalance;

  // Check URL params (after Adsterra return)
  const urlParams = new URLSearchParams(window.location.search);
  const step = urlParams.get("step");

  if (step) {
    currentStep = parseInt(step) + 1;
    if (currentStep <= questions.length) {
      showQuestion(currentStep);
    } else {
      showRewardSection();
    }
  } else {
    // Start fresh
    showQuestion(1);
  }
}

// Start Survey
async function startSurvey() {
    if (!userId) {
        console.error("No Telegram user ID!");
        return;
    }
    const res = await fetch(`${BACKEND_URL}/api/start-survey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_id: userId })
    });
  const data = await res.json();
  sessionId = data.session_id;
}

// Select Answer
function selectAnswer(index, answer) {
  document
    .querySelectorAll(".option-btn")
    .forEach((btn) => (btn.disabled = true));

  // ✅ FIXED: Use BACKEND_URL
  fetch(`${BACKEND_URL}/api/submit-answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      telegram_id: userId,
      session_id: sessionId,
      step: currentStep,
      answer: answer,
    }),
  }).then((response) => {
    if (response.status === 307) {
      window.location.href = response.url; // Redirect to Adsterra DL
    }
  });
}

// Claim Reward
document.getElementById("claimBtn")?.addEventListener("click", async () => {
  // ✅ FIXED: Use BACKEND_URL
  const res = await fetch(
    `${BACKEND_URL}/api/claim-reward?telegram_id=${userId}`
  );
  const data = await res.json();
  starBalance += data.stars;
  document.getElementById("starBalance").innerText = starBalance;
  alert(data.message);
  document.getElementById("claimBtn").style.display = "none";
});

// Spend Stars
async function spendStars(amount, action) {
  if (starBalance < amount) {
    alert("Not enough Stars! Complete more surveys.");
    return;
  }

  // ✅ FIXED: Use BACKEND_URL
  const res = await fetch(`${BACKEND_URL}/api/spend-stars`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      telegram_id: userId,
      amount: amount,
      action: action,
    }),
  });

  if (res.status === 307) {
    starBalance -= amount;
    document.getElementById("starBalance").innerText = starBalance;
    window.location.href = res.url;
  } else {
    const error = await res.json();
    alert(error.detail);
  }
}

// Redeem Stars
async function redeemStars() {
  if (starBalance < 500) {
    alert("Need 500 Stars to redeem!");
    return;
  }

  // ✅ FIXED: Use BACKEND_URL
  const res = await fetch(`${BACKEND_URL}/api/redeem-stars`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telegram_id: userId }),
  });

  const data = await res.json();
  alert(data.message);
  starBalance -= 500;
  document.getElementById("starBalance").innerText = starBalance;
}

// Show Reward Section (no fetch — safe)
async function showRewardSection() {
  document.getElementById("surveySection").style.display = "none";
  document.getElementById("rewardSection").style.display = "block";

  const fortunes = [
    "You're a: CRYPTO WHALE IN HIDING 🐋<br>🔮 2025 Income: $27,400<br>🌍 Travel: 4 countries",
    "You're a: WOLF OF WALL STREET 🐺<br>🔮 2025 Income: $50,000<br>🌍 Travel: 2 countries",
    "You're a: SLY FOX TRADER 🦊<br>🔮 2025 Income: $15,000<br>🌍 Travel: 6 countries",
  ];
  document.getElementById("fortuneResult").innerHTML =
    fortunes[Math.floor(Math.random() * fortunes.length)];

  setTimeout(() => {
    document.getElementById("starShop").style.display = "block";
  }, 1000);
}

// Show Question (no fetch — safe)
function showQuestion(step) {
  document.getElementById("surveySection").style.display = "block";
  document.getElementById("rewardSection").style.display = "none";
  document.getElementById("starShop").style.display = "none";

  const q = questions[step - 1];
  let html = `<h3>Q${step}: ${q.text}</h3>`;
  q.options.forEach((opt, i) => {
    html += `<button class="option-btn" onclick="selectAnswer(${i}, '${opt}')">${opt}</button>`;
  });
  document.getElementById("questionContainer").innerHTML = html;
  currentStep = step;
}

// Start!
startSurvey();
init();
