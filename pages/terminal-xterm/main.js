import { Terminal } from 'https://cdn.jsdelivr.net/npm/@xterm/xterm@5.3.0/+esm';
import { FitAddon } from 'https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.9.0/+esm';

const term = new Terminal({
  convertEol: true,
  fontSize: 15,
  theme: {
    background: '#07090c',
    foreground: '#e8ecf0',
    cursor: '#f25f26',
  },
});

const fitAddon = new FitAddon();
term.loadAddon(fitAddon);
term.open(document.getElementById('terminal'));
fitAddon.fit();

const intro = [
  '$ whoami',
  'tim fin — building sparse, stark systems',
  '',
  '$ ls work/',
  'terminal-concepts    prototyping        ml-tools',
  '',
  '$ ./demo.sh',
  'booting xterm.js …',
  'connected. use this shell to explore ideas.\n',
];

let index = 0;
function writeNextLine() {
  if (index >= intro.length) return;
  const line = intro[index];
  term.writeln(line);
  index += 1;
  setTimeout(writeNextLine, line.startsWith('$') ? 300 : 200);
}

writeNextLine();

window.addEventListener('resize', () => fitAddon.fit());

term.prompt = () => {
  term.write('\r\n$ ');
};

term.onKey(({ key, domEvent }) => {
  const char = key;
  if (domEvent.key === 'Enter') {
    term.prompt();
  } else if (domEvent.key === 'Backspace') {
    term.write('\b \b');
  } else if (domEvent.key.length === 1) {
    term.write(char);
  }
});

term.focus();
term.write('$ ');
