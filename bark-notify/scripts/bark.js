#!/usr/bin/env node

/**
 * Bark 推送通知 CLI
 * 
 * 用法:
 *   bark notify "标题" "内容" [选项]
 *   bark sound [铃声名]          # 列出/设置铃声
 *   bark badge [数字]            # 设置角标
 *   bark config [key] [value]    # 查看/修改配置
 *   bark test                    # 测试推送
 *   bark sounds                  # 列出所有铃声
 *   bark badges                  # 列出角标预设
 * 
 * 示例:
 *   bark notify "任务完成" "备份成功"
 *   bark notify -s alarm -g 监控 "告警" "CPU过高"
 *   bark badge 5
 *   bark sound alarm
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// ============ 配置 ============

const SKILL_DIR = path.dirname(__dirname);
const CONFIG_PATH = path.join(SKILL_DIR, 'config.json');
const SOUNDS_PATH = path.join(SKILL_DIR, 'sounds.json');
const BADGES_PATH = path.join(SKILL_DIR, 'badges.json');

function loadConfig() {
  try {
    if (!fs.existsSync(CONFIG_PATH)) {
      console.error('❌ 配置文件不存在:', CONFIG_PATH);
      console.error('请复制 config.example.json 为 config.json 并填入你的 key');
      process.exit(1);
    }
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
  } catch (e) {
    console.error('❌ 配置文件读取失败:', e.message);
    process.exit(1);
  }
}

function saveConfig(config) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf-8');
}

function loadSounds() {
  try {
    return JSON.parse(fs.readFileSync(SOUNDS_PATH, 'utf-8'));
  } catch (e) {
    return { sounds: {} };
  }
}

function loadBadges() {
  try {
    return JSON.parse(fs.readFileSync(BADGES_PATH, 'utf-8'));
  } catch (e) {
    return { badges: {} };
  }
}

// ============ 网络请求 ============

function sendRequest(url, data) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const client = urlObj.protocol === 'https:' ? https : http;
    
    const postData = JSON.stringify(data);
    
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Length': Buffer.byteLength(postData)
      },
      timeout: 10000
    };

    const req = client.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          resolve({ code: -1, msg: body });
        }
      });
    });

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });

    req.write(postData);
    req.end();
  });
}

// ============ 核心功能 ============

async function notify(title, body, options = {}) {
  const config = loadConfig();
  
  const payload = {
    title: title || '通知',
    body: body || new Date().toLocaleTimeString('zh-CN') + ' 完成',
    sound: options.sound || config.default_sound || 'calypso',
    group: options.group || config.default_group || 'Pi'
  };

  // 添加可选参数
  if (options.level) payload.level = options.level;
  if (options.icon) payload.icon = options.icon;
  if (options.url) payload.url = options.url;
  if (options.image) payload.image = options.image;
  if (options.badge !== undefined) payload.badge = options.badge;
  if (options.copy) payload.copy = options.copy;
  if (options.markdown) payload.markdown = options.markdown;
  if (options.subtitle) payload.subtitle = options.subtitle;

  // 穿透专注模式的快捷方式
  if (options.timeSensitive) payload.level = 'timeSensitive';

  const url = `${config.server}/${config.key}`;
  
  try {
    const result = await sendRequest(url, payload);
    if (result.code === 200) {
      console.log(`✅ 推送成功: ${title}`);
      return { success: true, data: result };
    } else {
      console.log(`❌ 推送失败: ${result.msg || JSON.stringify(result)}`);
      return { success: false, error: result };
    }
  } catch (e) {
    console.error(`❌ 请求错误: ${e.message}`);
    return { success: false, error: e.message };
  }
}

async function setBadge(badge) {
  const config = loadConfig();
  const url = `${config.server}/${config.key}`;
  
  const payload = {
    badge: parseInt(badge),
    body: ' '  // 空内容只更新角标
  };

  try {
    const result = await sendRequest(url, payload);
    if (result.code === 200) {
      console.log(`✅ 角标已设置为: ${badge}`);
      return true;
    }
    return false;
  } catch (e) {
    console.error(`❌ 设置角标失败: ${e.message}`);
    return false;
  }
}

// ============ 命令行解析 ============

function parseArgs(args) {
  const result = {
    command: null,
    positional: [],
    options: {}
  };

  let i = 0;
  // 跳过 node 和脚本路径
  if (args[0] && !args[0].startsWith('-')) {
    result.command = args[0];
    i = 1;
  }

  while (i < args.length) {
    const arg = args[i];
    if (arg.startsWith('-')) {
      const key = arg.replace(/^-+/, '');
      // 布尔选项
      if (key === 'time-sensitive' || key === 't' || key === 'l') {
        result.options[key] = true;
        i++;
      } else {
        // 带值的选项
        result.options[key] = args[i + 1];
        i += 2;
      }
    } else {
      result.positional.push(arg);
      i++;
    }
  }

  return result;
}

// ============ 帮助信息 ============

function showHelp() {
  console.log(`
🔔 Bark 推送通知 CLI

用法:
  bark notify "标题" "内容" [选项]    # 发送推送
  bark badge <数字>                   # 设置角标
  bark sound [铃声名]                 # 查看/设置铃声
  bark config [key] [value]           # 查看/修改配置
  bark sounds                         # 列出所有铃声
  bark badges                         # 列出角标预设
  bark test                           # 测试推送
  bark help                           # 显示帮助

选项:
  -s, --sound <铃声>     自定义铃声
  -g, --group <分组>     消息分组
  -l, --level <级别>     推送级别 (active/timeSensitive/passive/critical)
  --time-sensitive       时效性通知（穿透专注模式）
  --icon <url>           自定义图标 URL
  --url <url>            点击跳转链接
  --image <url>          推送图片 URL
  --subtitle <文本>      推送副标题
  --copy <文本>          复制到剪贴板
  --markdown <内容>      Markdown 格式正文

示例:
  bark notify "任务完成" "备份成功"
  bark notify -s alarm -g 监控 "告警" "CPU过高"
  bark notify --time-sensitive "紧急" "需要立即处理"
  bark badge 5
  `);
}

function showSounds() {
  const sounds = loadSounds();
  console.log('\n🎵 可用铃声:\n');
  
  const categories = {};
  for (const [name, info] of Object.entries(sounds.sounds)) {
    const cat = info.category || 'other';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push({ name, ...info });
  }

  for (const [cat, items] of Object.entries(categories)) {
    console.log(`【${sounds.categories[cat] || cat}】`);
    for (const item of items) {
      console.log(`  ${item.name.padEnd(12)} - ${item.description}`);
    }
    console.log('');
  }
}

function showBadges() {
  const badges = loadBadges();
  console.log('\n🔢 角标预设:\n');
  
  for (const [value, info] of Object.entries(badges.badges)) {
    console.log(`  ${value.padEnd(6)} - ${info.description}`);
    if (info.use_case) {
      console.log(`${''.padEnd(9)}用途: ${info.use_case}`);
    }
    console.log('');
  }

  console.log('\n📊 快捷预设:');
  for (const [name, value] of Object.entries(badges.presets)) {
    console.log(`  ${name.padEnd(10)} = ${value}`);
  }
}

function showConfig() {
  const config = loadConfig();
  console.log('\n⚙️  当前配置:\n');
  console.log(`  服务器: ${config.server}`);
  console.log(`  Key: ${config.key}`);
  console.log(`  默认铃声: ${config.default_sound}`);
  console.log(`  默认分组: ${config.default_group}`);
  console.log(`  默认级别: ${config.default_level}`);
}

// ============ 主函数 ============

async function main() {
  const args = parseArgs(process.argv.slice(2));
  
  if (!args.command || args.command === 'help') {
    showHelp();
    return;
  }

  switch (args.command) {
    case 'notify':
    case 'send':
    case 'push': {
      const title = args.positional[0];
      const body = args.positional[1];
      
      if (!title && !body) {
        console.error('❌ 请提供标题或内容');
        console.log('用法: bark notify "标题" "内容"');
        return;
      }

      const options = {
        sound: args.options.s || args.options.sound,
        group: args.options.g || args.options.group,
        level: args.options.l || args.options.level,
        timeSensitive: args.options.timeSensitive,
        icon: args.options.icon,
        url: args.options.url,
        image: args.options.image,
        subtitle: args.options.subtitle,
        copy: args.options.copy,
        markdown: args.options.markdown,
        badge: args.options.badge
      };

      await notify(title, body, options);
      break;
    }

    case 'badge':
    case 'icon': {
      if (args.positional.length === 0) {
        console.log('当前需要手动查看角标');
        showBadges();
        return;
      }
      await setBadge(args.positional[0]);
      break;
    }

    case 'sound':
    case 'ringtone': {
      if (args.positional.length === 0) {
        const config = loadConfig();
        console.log(`当前默认铃声: ${config.default_sound}`);
        showSounds();
        return;
      }
      
      const config = loadConfig();
      config.default_sound = args.positional[0];
      saveConfig(config);
      console.log(`✅ 默认铃声已设置为: ${args.positional[0]}`);
      break;
    }

    case 'config':
    case 'setting': {
      if (args.positional.length === 0) {
        showConfig();
        return;
      }
      
      if (args.positional.length === 1) {
        const config = loadConfig();
        console.log(`${args.positional[0]}: ${config[args.positional[0]] || '未设置'}`);
        return;
      }

      const config = loadConfig();
      const key = args.positional[0];
      const value = args.positional[1];
      
      // 尝试解析 JSON 值
      try {
        config[key] = JSON.parse(value);
      } catch {
        config[key] = value;
      }
      
      saveConfig(config);
      console.log(`✅ ${key} 已设置为: ${value}`);
      break;
    }

    case 'sounds':
    case 'ringtones': {
      showSounds();
      break;
    }

    case 'badges': {
      showBadges();
      break;
    }

    case 'test': {
      console.log('🧪 发送测试推送...');
      await notify('🔔 测试推送', `测试时间: ${new Date().toLocaleString('zh-CN')}`, {
        sound: 'complete'
      });
      break;
    }

    default:
      console.error(`❌ 未知命令: ${args.command}`);
      showHelp();
  }
}

// 导出供其他脚本使用
module.exports = { notify, setBadge, loadConfig, loadSounds, loadBadges };

// 命令行执行
if (require.main === module) {
  main().catch(console.error);
}
