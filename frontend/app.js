const tg = window.Telegram.WebApp;
tg.expand();

let userId = tg.initDataUnsafe?.user?.id || 5138176448;
let userFirstName = tg.initDataUnsafe?.user?.first_name || "Anonymous";
let userPhoto =
  tg.initDataUnsafe?.user?.photo_url || "https://via.placeholder.com/40";

let sessionId = null;
let currentStep = 1;
let starBalance = 0;
let surveysCompleted = 0;
let friendsReferred = 0;

const ADSTERRA_DL_URL =
  "https://hushclosing.com/t1r95sski9?key=54ee15c5b03f8b5b1222da89c95a2e13";
const BACKEND_URL = "https://quizzy-tg-mini-app-backend.onrender.com".trim();
//const BACKEND_URL = "http://localhost:8000".trim();

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
  document.getElementById("userName").innerText = userFirstName;
  document.getElementById("userAvatar").src = userPhoto;

  if (!userId) {
    alert("Please open this app inside Telegram!");
    return;
  }

  try {
    const user = await fetch(
      `${BACKEND_URL}/api/user?telegram_id=${userId}`
    ).then((r) => r.json());
    starBalance = user.virtual_stars || 0;
    surveysCompleted = user.surveys_completed || 0;
    friendsReferred = user.friends_referred || 0;
    document.getElementById("starBalance").innerText = `🌟 ${starBalance}`;
    document.getElementById("totalStars").innerText = starBalance;
    document.getElementById("surveysCompleted").innerText = surveysCompleted;
    document.getElementById("friendsReferred").innerText = friendsReferred;

    if (!user.first_survey_completed) {
      showFirstSurveyModal();
    } else {
      showPage("surveyPage");
      loadSurveys();
    }

    // Set referral link
    document.getElementById(
      "referralLink"
    ).innerText = `t.me/Quizzy_app_bot?start=ref${userId}`;
  } catch (e) {
    showToast("Backend error — running with default values");
    showPage("surveyPage");
  }

  startSurvey();
}

// Show Page
function showPage(pageId) {
  document.querySelectorAll(".page").forEach((p) => (p.style.display = "none"));
  document
    .querySelectorAll(".nav-btn")
    .forEach((b) => b.classList.remove("active"));
  document.getElementById(pageId).style.display = "block";
  event.target.classList.add("active");
}

// Show First Survey Modal
function showFirstSurveyModal() {
  document.getElementById("firstSurveyModal").style.display = "block";
  document
    .getElementById("startFirstSurveyBtn")
    .addEventListener("click", () => {
      document.getElementById("firstSurveyModal").style.display = "none";
      showSurveyModal();
    });
}

// Show Survey Modal
function showSurveyModal() {
  document.getElementById("surveySection").style.display = "block";
  showQuestion(1);
}

// Show Question
function showQuestion(step) {
  document.getElementById("surveyTitle").innerText = `Q${step}: ${
    questions[step - 1].text
  }`;
  let html = "";
  questions[step - 1].options.forEach((opt, i) => {
    html += `<button class="option-btn" onclick="selectAnswer(${i}, '${opt}')">${opt}</button>`;
  });
  document.getElementById("questionContainer").innerHTML = html;
  currentStep = step;
}

// Select Answer
function selectAnswer(index, answer) {
  window.open(ADSTERRA_DL_URL, "_blank");
  logAnswerToBackend(answer);

  currentStep += 1;
  if (currentStep <= questions.length) {
    showQuestion(currentStep);
  } else {
    showRewardModal();
  }
}

// Log Answer
async function logAnswerToBackend(answer) {
  try {
    await fetch(`${BACKEND_URL}/api/submit-answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        telegram_id: userId,
        session_id: sessionId,
        step: currentStep,
        answer: answer,
      }),
    });
  } catch (e) {
    console.log("Failed to log answer");
  }
}

// Start Survey
async function startSurvey() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/start-survey`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telegram_id: userId }),
    });
    const data = await res.json();
    sessionId = data.session_id;
  } catch (e) {
    console.log("Failed to start survey session");
  }
}

// Show Reward Modal
function showRewardModal() {
  document.getElementById("surveySection").style.display = "none";
  document.getElementById("rewardSection").style.display = "block";

  const fortunes = [
    "You're a: CRYPTO WHALE IN HIDING 🐋<br>🔮 2025 Income: $27,400<br>🌍 Travel: 4 countries",
    "You're a: WOLF OF WALL STREET 🐺<br>🔮 2025 Income: $50,000<br>🌍 Travel: 2 countries",
    "You're a: SLY FOX TRADER 🦊<br>🔮 2025 Income: $15,000<br>🌍 Travel: 6 countries",
  ];
  document.getElementById("fortuneResult").innerHTML =
    fortunes[Math.floor(Math.random() * fortunes.length)];
}

// Claim Reward
document.getElementById("claimBtn")?.addEventListener("click", async () => {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/claim-reward?telegram_id=${userId}`
    );
    const data = await res.json();
    starBalance += data.stars;
    document.getElementById("starBalance").innerText = `🌟 ${starBalance}`;
    document.getElementById("totalStars").innerText = starBalance;
    showToast("🎉 50 Stars Credited!");
    document.getElementById("rewardSection").style.display = "none";
    showPage("surveyPage");
    loadSurveys();
  } catch (e) {
    showToast("Failed to claim reward");
  }
});
// Watch Ad → Earn Stars
async function watchAdForStars(stars) {
    try {
        // Show Rewarded Interstitial
        await show_9845275();
        
        // Reward user
        starBalance += stars;
        document.getElementById("starBalance").innerText = `🌟 ${starBalance}`;
        document.getElementById("totalStars").innerText = starBalance;
        showToast(`🎉 ${stars} Stars Credited!`);

        // Log to backend
        await fetch(`${BACKEND_URL}/api/spend-stars`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: userId,
                amount: -stars, // Negative because we're "spending" nothing — just logging
                action: "watch_ad"
            })
        });

        // Log transaction
        await fetch(`${BACKEND_URL}/api/claim-reward`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

    } catch (e) {
        showToast("Ad failed — no stars earned");
    }
}
async function watchAdPopupForStars(stars) {
    try {
        await show_9845275('pop');
        starBalance += stars;
        document.getElementById("starBalance").innerText = `🌟 ${starBalance}`;
        showToast(`🎉 ${stars} Stars Credited!`);
    } catch (e) {
        showToast("Popup ad failed");
    }
}

// Auto-show in-app interstitial every 5 minutes
setInterval(() => {
    show_9845275({
        type: 'inApp',
        inAppSettings: {
            frequency: 1,
            capping: 0.1,
            interval: 30,
            timeout: 5,
            everyPage: false
        }
    }).catch(e => console.log("In-app ad failed"));
}, 5 * 60 * 1000); // 5 minutes

// Load Surveys
async function loadSurveys() {
  // Show skeleton loaders
  document.getElementById("incomingList").innerHTML =
    '<div class="skeleton" style="width: 80%;"></div><div class="skeleton" style="width: 60%;"></div>';
  document.getElementById("completedList").innerHTML =
    '<div class="skeleton" style="width: 80%;"></div>';

  try {
    const user = await fetch(
      `${BACKEND_URL}/api/user?telegram_id=${userId}`
    ).then((r) => r.json());
    const sessions = await fetch(
      `${BACKEND_URL}/api/survey-sessions?telegram_id=${userId}`
    ).then((r) => r.json());

    // Incoming Surveys
    let incomingHtml = "";
    if (!user.first_survey_completed) {
      incomingHtml += `<div class="task-card"><h3>First Survey (50 Stars)</h3><button onclick="showSurveyModal()" class="btn">Start →</button></div>`;
    }
    document.getElementById("incomingList").innerHTML =
      incomingHtml || "<p>No incoming surveys</p>";

    // Completed Surveys
    let completedHtml = "";
    sessions.forEach((session) => {
      if (session.completed_at) {
        completedHtml += `<p>✅ Survey completed on ${new Date(
          session.completed_at
        ).toLocaleDateString()}</p>`;
      }
    });
    document.getElementById("completedList").innerHTML =
      completedHtml || "<p>No completed surveys</p>";
  } catch (e) {
    document.getElementById("incomingList").innerHTML =
      "<p>Failed to load surveys</p>";
    document.getElementById("completedList").innerHTML =
      "<p>Failed to load surveys</p>";
  }
}

// Join Channel
function joinChannel() {
  window.open("https://t.me/yourchannel", "_blank");
  document.getElementById("claimChannelBtn").style.display = "block";
}

// Claim Channel Reward
async function claimChannelReward() {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/claim-channel-reward?telegram_id=${userId}`
    );
    const data = await res.json();
    starBalance += data.stars;
    document.getElementById("starBalance").innerText = `🌟 ${starBalance}`;
    document.getElementById("totalStars").innerText = starBalance;
    showToast("🎉 10 Stars Credited!");
    document.getElementById("claimChannelBtn").style.display = "none";
  } catch (e) {
    showToast("Failed to claim reward");
  }
}

// Copy Referral Link
function copyRefLink() {
  const link = `t.me/Quizzy_app_bot?start=ref${userId}`;
  navigator.clipboard.writeText(link);
  showToast("Link copied to clipboard!");
}

// Show Redeem Modal
function showRedeemModal() {
  if (starBalance < 2000) {
    showToast("Need 2000 Stars to redeem!");
    return;
  }
  document.getElementById("redeemModal").style.display = "block";
}

// Submit Redeem
async function submitRedeem() {
  const name = document.getElementById("paymentName").value;
  const email = document.getElementById("paymentEmail").value;

  if (!name || !email) {
    showToast("Please fill all fields");
    return;
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/redeem-stars`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        telegram_id: userId,
        payment_name: name,
        payment_email: email,
      }),
    });

    const data = await res.json();
    showToast(data.message);
    if (data.success) {
      starBalance -= 2000;
      document.getElementById("starBalance").innerText = `🌟 ${starBalance}`;
      document.getElementById("totalStars").innerText = starBalance;
      document.getElementById("redeemModal").style.display = "none";
    }
  } catch (e) {
    showToast("Failed to redeem");
  }
}

// Toast
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.innerText = message;
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3000);
}

// Start!
init();
