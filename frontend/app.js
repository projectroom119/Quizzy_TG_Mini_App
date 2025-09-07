const tg = window.Telegram.WebApp;
tg.expand();

// Fallback for browser testing
let userId = tg.initDataUnsafe?.user?.id || 5138176448;

let sessionId = null;
let currentStep = 1;
let starBalance = 0;

// Your Adsterra Direct Link
const ADSTERRA_DL_URL =
  "https://hushclosing.com/t1r95sski9?key=54ee15c5b03f8b5b1222da89c95a2e13";

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

  // Optional: Fetch user data (if you want to keep star balance)
  try {
    const user = await fetch(
      `${BACKEND_URL}/api/user?telegram_id=${userId}`
    ).then((r) => r.json());
    starBalance = user.virtual_stars || 0;
    document.getElementById("starBalance").innerText = starBalance;
  } catch (e) {
    console.log("Backend down — running in simple mode");
  }

  // Check URL params (if you ever want to use them later)
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
    showQuestion(1);
  }
}

// Show Question
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

// Select Answer — SIMPLIFIED
function selectAnswer(index, answer) {
  // 1. Open Adsterra DL in new tab
  window.open(ADSTERRA_DL_URL, "_blank");

  // 2. Immediately show next question (no waiting, no backend call)
  currentStep += 1;
  if (currentStep <= questions.length) {
    showQuestion(currentStep);
  } else {
    showRewardSection();
  }
}

// Start Survey — SIMPLIFIED (no backend call needed)
async function startSurvey() {
  // Optional: If you want to log session start, keep this
  /*
    try {
        const res = await fetch(`${BACKEND_URL}/api/start-survey`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: userId })
        });
        const data = await res.json();
        sessionId = data.session_id;
    } catch (e) {
        console.log("Backend down — running in simple mode");
    }
    */
}

// Show Reward Section
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

// Claim Reward (keep if you want)
document.getElementById("claimBtn")?.addEventListener("click", async () => {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/claim-reward?telegram_id=${userId}`
    );
    const data = await res.json();
    starBalance += data.stars;
    document.getElementById("starBalance").innerText = starBalance;
    alert(data.message);
    document.getElementById("claimBtn").style.display = "none";
  } catch (e) {
    alert("Backend down — reward not claimed");
  }
});

// Spend Stars (keep if you want)
async function spendStars(amount, action) {
  if (starBalance < amount) {
    alert("Not enough Stars! Complete more surveys.");
    return;
  }

  try {
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
  } catch (e) {
    alert("Backend down — stars not spent");
  }
}

// Redeem Stars (keep if you want)
async function redeemStars() {
  if (starBalance < 500) {
    alert("Need 500 Stars to redeem!");
    return;
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/redeem-stars`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telegram_id: userId }),
    });

    const data = await res.json();
    alert(data.message);
    starBalance -= 500;
    document.getElementById("starBalance").innerText = starBalance;
  } catch (e) {
    alert("Backend down — not redeemed");
  }
}

// Start!
startSurvey();
init();
