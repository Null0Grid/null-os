# User programs (Claude Code, pipx)
[[ -d ~/.local/bin ]] && path=(~/.local/bin $path)

# ~/.zshrc — Null OS default zsh config

setopt autocd interactivecomments magicequalsubst nonomatch notify numericglobsort promptsubst
WORDCHARS=${WORDCHARS//\/}
PROMPT_EOL_MARK=""

# ---- History ----
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=20000
setopt hist_expire_dups_first hist_ignore_dups hist_ignore_space hist_verify share_history

# ---- Completion ----
autoload -Uz compinit && compinit -d ~/.cache/zcompdump
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' rehash true

# ---- Keys ----
bindkey -e
bindkey '^[[1;5C' forward-word
bindkey '^[[1;5D' backward-word
bindkey '^[[H' beginning-of-line
bindkey '^[[F' end-of-line
bindkey '^[[3~' delete-char

# ---- Null mark ----
# The mark lives at U+E900 in the Null Mono font. It's used in local
# graphical terminals. Over SSH or on the bare console the font may be
# missing, so fall back to a plain @. Override with NULL_GLYPH=1 or 0.
if [[ -z $NULL_GLYPH ]]; then
  if [[ -n $SSH_CONNECTION || $TERM == linux ]]; then NULL_GLYPH=0; else NULL_GLYPH=1; fi
fi
if (( NULL_GLYPH )); then NULL_SEP=$''; else NULL_SEP='@'; fi

# ---- Neon Lab colours (truecolor, with 256-colour fallback) ----
if [[ $COLORTERM == (truecolor|24bit) ]]; then
  _c_frame='#00e5ff' _c_user='#ff2e88' _c_path='#3dff7a' _c_err='#ff4d4d' _c_dim='#7f8fa6'
else
  _c_frame=51 _c_user=198 _c_path=84 _c_err=203 _c_dim=103
fi

# ---- Git branch segment ----
autoload -Uz vcs_info add-zsh-hook
zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:git:*' formats '%b'
zstyle ':vcs_info:git:*' actionformats '%b|%a'
_null_vcs() { vcs_info }
add-zsh-hook precmd _null_vcs

# ---- Two-line prompt ----
#   ┌──(user<mark>host)-[~/path]-[branch]-[✗ code]
#   └─$
# Frame turns red for root, and the prompt char becomes #.
_null_prompt() {
  local frame=$_c_frame
  (( EUID == 0 )) && frame=$_c_err
  local p="%F{$frame}┌──(%B%F{$_c_user}%n${NULL_SEP}%m%b%F{$frame})-[%B%F{$_c_path}%(6~.%-1~/…/%4~.%5~)%b%F{$frame}]"
  [[ -n ${vcs_info_msg_0_} ]] && p+="-[%F{$_c_dim}${vcs_info_msg_0_}%F{$frame}]"
  p+="%(?..-[%F{$_c_err}✗ %?%F{$frame}])"
  p+=$'\n'"%F{$frame}└─%B%(#.%F{$_c_err}#.%F{$frame}\$)%b%f "
  PROMPT=$p
}
add-zsh-hook precmd _null_prompt

# Blank line between commands, like Kali (skipped before the first prompt)
_null_newline() { [[ -n $_null_first ]] && print; _null_first=1 }
add-zsh-hook precmd _null_newline

# ---- Plugins (Debian packages) ----
[[ -r /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && {
  source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
  ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=$_c_dim"
}
[[ -r /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && {
  source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  typeset -A ZSH_HIGHLIGHT_STYLES
  ZSH_HIGHLIGHT_STYLES[command]="fg=$_c_path,bold"
  ZSH_HIGHLIGHT_STYLES[builtin]="fg=$_c_path,bold"
  ZSH_HIGHLIGHT_STYLES[alias]="fg=$_c_path,bold"
  ZSH_HIGHLIGHT_STYLES[unknown-token]="fg=$_c_err,bold"
  ZSH_HIGHLIGHT_STYLES[path]="fg=$_c_frame,underline"
  ZSH_HIGHLIGHT_STYLES[single-quoted-argument]="fg=$_c_user"
  ZSH_HIGHLIGHT_STYLES[double-quoted-argument]="fg=$_c_user"
}

# ---- Aliases ----
alias ls='ls --color=auto'
alias ll='ls -lh'
alias la='ls -lAh'
alias grep='grep --color=auto'
alias ip='ip --color=auto'
alias diff='diff --color=auto'
