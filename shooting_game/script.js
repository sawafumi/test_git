const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const scoreEl = document.getElementById('score');
const livesEl = document.getElementById('lives');
const waveEl = document.getElementById('wave');
const restartButton = document.getElementById('restart');

const width = canvas.width;
const height = canvas.height;

const player = {
  x: width / 2 - 20,
  y: height - 70,
  w: 40,
  h: 40,
  speed: 5,
  cooldown: 0
};

const state = {
  running: true,
  score: 0,
  lives: 3,
  wave: 1,
  enemySpeed: 1.3,
  enemyShootChance: 0.002
};

const keys = {
  left: false,
  right: false,
  shoot: false
};

const bullets = [];
const enemyBullets = [];
let enemies = [];
const stars = Array.from({ length: 80 }, () => ({
  x: Math.random() * width,
  y: Math.random() * height,
  size: Math.random() * 2 + 0.5,
  speed: Math.random() * 0.6 + 0.2
}));

function resetGame() {
  state.running = true;
  state.score = 0;
  state.lives = 3;
  state.wave = 1;
  state.enemySpeed = 1.3;
  state.enemyShootChance = 0.002;
  bullets.length = 0;
  enemyBullets.length = 0;
  enemies = [];
  player.x = width / 2 - player.w / 2;
  player.cooldown = 0;
  spawnWave();
  restartButton.hidden = true;
}

function spawnWave() {
  const rows = Math.min(3 + state.wave, 6);
  const perRow = 6;
  const padding = 60;
  const gapX = (width - padding * 2) / (perRow - 1);
  const gapY = 60;

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < perRow; col += 1) {
      enemies.push({
        x: padding + col * gapX - 20,
        y: 60 + row * gapY,
        w: 40,
        h: 30,
        vx: (Math.random() * 2 - 1) * 0.6,
        vy: state.enemySpeed,
        life: 1
      });
    }
  }
}

function updateStars(dt) {
  for (const star of stars) {
    star.y += star.speed * dt * 60;
    if (star.y > height) {
      star.y = -star.size;
      star.x = Math.random() * width;
      star.speed = Math.random() * 0.6 + 0.2;
    }
  }
}

function updatePlayer(dt) {
  if (keys.left) {
    player.x -= player.speed * dt * 60;
  }
  if (keys.right) {
    player.x += player.speed * dt * 60;
  }
  player.x = Math.max(0, Math.min(width - player.w, player.x));

  if (player.cooldown > 0) {
    player.cooldown -= dt;
  }

  if (keys.shoot && player.cooldown <= 0) {
    bullets.push({
      x: player.x + player.w / 2 - 3,
      y: player.y,
      w: 6,
      h: 12,
      speed: 9
    });
    player.cooldown = 0.3;
  }
}

function updateBullets(dt) {
  for (let i = bullets.length - 1; i >= 0; i -= 1) {
    const bullet = bullets[i];
    bullet.y -= bullet.speed * dt * 60;
    if (bullet.y + bullet.h < 0) {
      bullets.splice(i, 1);
      continue;
    }

    for (let j = enemies.length - 1; j >= 0; j -= 1) {
      const enemy = enemies[j];
      if (intersects(bullet, enemy)) {
        bullets.splice(i, 1);
        enemy.life -= 1;
        state.score += 100;
        if (enemy.life <= 0) {
          enemies.splice(j, 1);
        }
        break;
      }
    }
  }
}

function updateEnemyBullets(dt) {
  for (let i = enemyBullets.length - 1; i >= 0; i -= 1) {
    const bullet = enemyBullets[i];
    bullet.y += bullet.speed * dt * 60;
    if (bullet.y > height) {
      enemyBullets.splice(i, 1);
      continue;
    }

    if (intersects(bullet, player)) {
      enemyBullets.splice(i, 1);
      damagePlayer();
    }
  }
}

function damagePlayer() {
  if (!state.running) return;
  state.lives -= 1;
  if (state.lives <= 0) {
    gameOver();
  }
}

function gameOver() {
  state.running = false;
  restartButton.hidden = false;
}

function updateEnemies(dt) {
  const difficultyBoost = 1 + state.wave * 0.1;
  for (let i = enemies.length - 1; i >= 0; i -= 1) {
    const enemy = enemies[i];
    enemy.x += enemy.vx * dt * 60;
    enemy.y += enemy.vy * dt * 60 * difficultyBoost;

    if (enemy.x < 10 || enemy.x + enemy.w > width - 10) {
      enemy.vx *= -1;
    }

    if (enemy.y + enemy.h > height - 80) {
      enemies.splice(i, 1);
      damagePlayer();
      continue;
    }

    if (Math.random() < state.enemyShootChance * difficultyBoost) {
      enemyBullets.push({
        x: enemy.x + enemy.w / 2 - 3,
        y: enemy.y + enemy.h,
        w: 6,
        h: 12,
        speed: 4 + state.wave * 0.25
      });
    }
  }

  if (enemies.length === 0 && state.running) {
    state.wave += 1;
    state.enemySpeed += 0.2;
    state.enemyShootChance = Math.min(0.01, state.enemyShootChance + 0.0015);
    spawnWave();
  }
}

function intersects(a, b) {
  return (
    a.x < b.x + b.w &&
    a.x + a.w > b.x &&
    a.y < b.y + b.h &&
    a.y + a.h > b.y
  );
}

function drawBackground() {
  ctx.fillStyle = '#020617';
  ctx.fillRect(0, 0, width, height);

  for (const star of stars) {
    ctx.fillStyle = `rgba(148, 163, 184, ${0.3 + Math.random() * 0.7})`;
    ctx.beginPath();
    ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawPlayer() {
  ctx.save();
  ctx.translate(player.x + player.w / 2, player.y + player.h / 2);
  ctx.fillStyle = '#38bdf8';
  ctx.beginPath();
  ctx.moveTo(0, -player.h / 2);
  ctx.lineTo(player.w / 2, player.h / 2);
  ctx.lineTo(-player.w / 2, player.h / 2);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawEnemies() {
  for (const enemy of enemies) {
    ctx.fillStyle = '#f97316';
    ctx.beginPath();
    drawRoundedRect(ctx, enemy.x, enemy.y, enemy.w, enemy.h, 6);
    ctx.fill();
    ctx.fillStyle = '#fb7185';
    ctx.fillRect(enemy.x + 10, enemy.y + 6, enemy.w - 20, 6);
  }
}

function drawRoundedRect(context, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  context.moveTo(x + r, y);
  context.lineTo(x + width - r, y);
  context.quadraticCurveTo(x + width, y, x + width, y + r);
  context.lineTo(x + width, y + height - r);
  context.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  context.lineTo(x + r, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - r);
  context.lineTo(x, y + r);
  context.quadraticCurveTo(x, y, x + r, y);
  context.closePath();
}

function drawBullets() {
  ctx.fillStyle = '#f8fafc';
  for (const bullet of bullets) {
    ctx.fillRect(bullet.x, bullet.y, bullet.w, bullet.h);
  }

  ctx.fillStyle = '#f87171';
  for (const bullet of enemyBullets) {
    ctx.fillRect(bullet.x, bullet.y, bullet.w, bullet.h);
  }
}

function drawGameOver() {
  if (state.running) return;
  ctx.fillStyle = 'rgba(2, 6, 23, 0.8)';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = '#f8fafc';
  ctx.font = 'bold 36px "Noto Sans JP", sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('ゲームオーバー', width / 2, height / 2 - 20);
  ctx.font = '24px "Noto Sans JP", sans-serif';
  ctx.fillText(`スコア: ${state.score}`, width / 2, height / 2 + 20);
}

let lastTime = performance.now();
function loop(now) {
  const dt = Math.min((now - lastTime) / 1000, 0.033);
  lastTime = now;

  updateStars(dt);

  if (state.running) {
    updatePlayer(dt);
    updateBullets(dt);
    updateEnemies(dt);
    updateEnemyBullets(dt);
  }

  drawBackground();
  drawPlayer();
  drawEnemies();
  drawBullets();
  drawGameOver();

  scoreEl.textContent = state.score;
  livesEl.textContent = state.lives;
  waveEl.textContent = state.wave;

  requestAnimationFrame(loop);
}

// Input handling
document.addEventListener('keydown', (event) => {
  if (event.code === 'ArrowLeft') {
    keys.left = true;
    event.preventDefault();
  } else if (event.code === 'ArrowRight') {
    keys.right = true;
    event.preventDefault();
  } else if (event.code === 'Space') {
    keys.shoot = true;
    event.preventDefault();
  }
});

document.addEventListener('keyup', (event) => {
  if (event.code === 'ArrowLeft') {
    keys.left = false;
  } else if (event.code === 'ArrowRight') {
    keys.right = false;
  } else if (event.code === 'Space') {
    keys.shoot = false;
  }
});

restartButton.addEventListener('click', resetGame);

spawnWave();
requestAnimationFrame(loop);
