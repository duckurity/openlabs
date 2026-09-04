%% openlabs labsheet class
%% One branded challenge sheet per lab. Clean white paper, Ink text, and
%% Ember as the only saturated accent. Funnel Display carries the display
%% hierarchy, Geist the body, Geist Mono the labels, metadata, and code.
%%
%% Design follows the openlabs brand spec: warm neutrals only, one accent
%% kept to small areas, flat surfaces, subtractive rules, generous
%% whitespace. The layout is a print translation of the Kami system.
%%
%% Compile with XeLaTeX. The generator (scripts/make_lab_pdf.py) loads the
%% fonts after defining \assetpath, then fills this class.
%%
%% Typographic system
%%   Every size is expressed with fontspec's \fontsize{}{} pair: an optical
%%   size plus an explicit leading. Tracking (LetterSpace) scales with size,
%%   never fixed: micro labels run wide (LetterSpace ~ 5-12), display type
%%   sits near zero. Hierarchy is built from weight + size + leading as a
%%   set, not size alone. Vertical spacing is pitched on a shared 3mm beat
%%   (\bsmall, \bbase, \bdouble) so all block distances are proportional.
%%
%% Provided by the generator:
%%   \labname          lab slug
%%   \assetpath        staging dir (fonts/ + PNG brand assets)
%%   \displayfont      Funnel Display family command
%%   \monofont         Geist Mono family command
%%
%% Provided here (usage in Labsheet.tex body):
%%   \eyebrow{text}          uppercase mono micro-label, letterspaced
%%   \labtitle{text}         display title
%%   \lead{text}             short description under the title
%%   \metric{label}{value}   labeled stat cell; Ember via [ember]
%%   \difficultybar{n}       4-segment meter (the one data graph)
%%   \cmdbox{command}        warm command pill with a prompt marker
%%   \section*               styled display heading
%%   lstlisting              warm-filled code card
%%   \bsmall \bbase \bdouble pitched vertical gaps
%%
%% Rated line: 10pt base, A4, 20mm margins.

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{labsheet}[2026/09/04 openlabs challenge sheet]
\LoadClass[10pt,a4paper]{article}

\RequirePackage{geometry}
\RequirePackage{xcolor}
\RequirePackage{fontspec}
\RequirePackage{titlesec}
\RequirePackage{fancyhdr}
\RequirePackage{tcolorbox}
\tcbuselibrary{skins,breakable}
\RequirePackage{array}
\RequirePackage{graphicx}
\RequirePackage{listings}
\RequirePackage{tikz}
\RequirePackage{microtype}

%% ---------------------------------------------------------------- geometry
%% Symmetric 20mm. Generous paper, room for the running header and a calm
%% rule-free footer. Text width gives a ~48-char measure at 10pt.
\geometry{
  a4paper,
  top=22mm, bottom=20mm, left=20mm, right=20mm,
  headheight=12mm, headsep=4mm, footskip=10mm,
}

%% ------------------------------------------------------------------ colors
%% One warm-neutral ramp plus a single saturated accent. Hierarchy runs down
%% the ramp: ink (primary), soft (lead), dim (micro-labels). Rules are a
%% cool-warm hairline so they sit on the paper rather than dividing it.
\definecolor{ink}{HTML}{1E1E1E}
\definecolor{soft}{HTML}{57524E}
\definecolor{dim}{HTML}{8A857F}
\definecolor{haire}{HTML}{E4E0DD}
\definecolor{warm}{HTML}{F4F2F1}
\definecolor{paper}{HTML}{FFFFFF}
\definecolor{ember}{HTML}{FF3616}
\definecolor{embertint}{HTML}{FFF0EC} % light tint on which ink Ember text sits

%% ---------------------------------------------------------------- typography
%% Body: Geist at 10pt on a 15.5pt leading, explicitly sized. Removes the
%% blunt \linespread{1.4} in favour of a tuned baseline.
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\renewcommand{\normalsize}{\fontsize{10}{15.5}\selectfont}

%% Pitched vertical rhythm. All block spacing is a multiple of this beat.
\newcommand{\bsmall}{\par\vspace{2.2mm}\par} % tight intra-block nudge
\newcommand{\bbase}{\par\vspace{3.4mm}\par}  % one beat between related blocks
\newcommand{\bdouble}{\par\vspace{7.2mm}\par}% two beats between sections

%% Micro-label: Geist Mono, tiny, wide leading, letterspaced, dim. The
%% lowest visual rung; every label in the system draws from this one voice.
\newcommand{\eyebrow}[1]{{%
  \monofont\fontsize{6.6}{9}\selectfont\addfontfeature{LetterSpace=14}%
  \color{dim}\MakeUppercase{#1}}}

%% ----------------------------------------------------------------- header
%% Calm, ruleless. Left is the mark, loosened, beside the word in display
%% weight. Right is the lab id in mono as a quiet anchor. Both sit on a
%% shared optical baseline; the mark is raised to balance against the
%% word's cap-height.
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyhead[L]{%
  \raisebox{2.0mm}{\includegraphics[height=5.6mm]{mark-cross-light.png}}%
  \hspace{2.6mm}%
  \raisebox{2.0mm}{{\displayfont\bfseries\fontsize{12}{14}\selectfont\color{ink} openlabs}}%
}
\fancyhead[R]{%
  \raisebox{2.0mm}{{\monofont\fontsize{7.6}{14}\selectfont\color{dim}\labname}}%
}
\fancyfoot[C]{%
  {\monofont\fontsize{7.6}{9}\selectfont\color{dim}openlabs}%
  \hspace{2.2mm}\textcolor{haire}{\textbullet}\hspace{2.2mm}%
  {\monofont\fontsize{7.6}{9}\selectfont\color{dim}page \thepage}%
}

%% ---------------------------------------------------------------- sections
%% Proximity law: gap under a heading is far smaller than the gap above, so
%% a heading reads as the opener of what follows, never the tail of the
%% previous block. Pure type hierarchy; no decorative ticks.
\titleformat{\section}
  {\displayfont\bfseries\fontsize{15}{19}\selectfont\color{ink}}
  {}{0em}{}
\titlespacing{\section}{0pt}{7.2mm}{2.2mm}

%% -------------------------------------------------------------------- rules
\newcommand{\hairline}{{\color{haire}\rule{\textwidth}{0.4pt}}}

%% --------------------------------------------------------------- masthead
%% A title that reads at a glance: display weight, tight leading, ink.
\newcommand{\labtitle}[1]{%
  \noindent{\displayfont\bfseries\fontsize{25}{28}\selectfont\color{ink}#1}%
}

%% The subtitle: one short line under the title, softer ink (soft), a touch
%% looser leading so it never crowds the display line.
\newcommand{\lead}[1]{%
  \noindent%
  \parbox{0.82\textwidth}{{\fontsize{10.5}{16}\selectfont\color{soft}#1}}%
}

%% -------------------------------------------------------------- metrics
%% A labeled stat cell: eyebrow over a one-line mono value. Four of these
%% sit in a row as a 4-column grid, split by the \mdimsep gutter so they
%% fill the measure. The optional Ember colour flags the single value a
%% reader must notice.
\newcommand{\metric}[3][ink]{%
  \begin{minipage}[t]{\dimexpr(\textwidth-\mdimsep*3)/4}
    \eyebrow{#2}\\[1.1mm]
    {\monofont\fontsize{12}{15}\selectfont\color{#1}#3}%
  \end{minipage}%
}
\newlength{\mdimsep}\setlength{\mdimsep}{5.4mm}

%% ----------------------------------------------------------- difficulty bar
%% The single data graph. Four equal segments fill the full measure; the
%% active rank fills Ember, the rest sit in a warm track. A shared legend
%% row below maps each column 1:1, centred so nothing ever overlaps; the
%% active label darkens to Ink, the rest recede to Dim. Ember carries the
%% whole accent budget of the sheet.
%%
%% Implemented unrolled (four segments), never a loop: pgf's value arithmetic
%% is too fragile inside \foreach for the per-column geometry. Each rectangle
%% and label is a single literal expression; the active rank is selected with
%% \ifcase. Switch level with \difficultybar{n}.
\newcommand{\difficultybar}[1]{%
  \def\dbar@cur{#1}%
  \pgfmathsetlengthmacro{\dbarw}{(\textwidth-\dbarsep*3)/4}%
  % Fill colour per rank.
  \def\dbarf@a{warm}\def\dbarf@b{warm}\def\dbarf@c{warm}\def\dbarf@d{warm}%
  \ifcase\dbar@cur\or\def\dbarf@a{ember}\or\def\dbarf@b{ember}%
     \or\def\dbarf@c{ember}\or\def\dbarf@d{ember}\fi
  % Label colour per rank.
  \def\dbaro@a{dim}\def\dbaro@b{dim}\def\dbaro@c{dim}\def\dbaro@d{dim}%
  \ifcase\dbar@cur\or\def\dbaro@a{ink}\or\def\dbaro@b{ink}%
     \or\def\dbaro@c{ink}\or\def\dbaro@d{ink}\fi
  \begin{tikzpicture}[baseline=0pt]
    \fill[\dbarf@a] (0,0) rectangle (1*\dbarw,3.4mm);
    \fill[\dbarf@b] (1*\dbarw+1*\dbarsep,0) rectangle (2*\dbarw+1*\dbarsep,3.4mm);
    \fill[\dbarf@c] (2*\dbarw+2*\dbarsep,0) rectangle (3*\dbarw+2*\dbarsep,3.4mm);
    \fill[\dbarf@d] (3*\dbarw+3*\dbarsep,0) rectangle (4*\dbarw+3*\dbarsep,3.4mm);
    \node[text=\dbaro@a] at (0.5*\dbarw,-2.2mm) {\monofont\fontsize{6.8}{8}\selectfont EASY};
    \node[text=\dbaro@b] at (1.5*\dbarw+1*\dbarsep,-2.2mm) {\monofont\fontsize{6.8}{8}\selectfont MEDIUM};
    \node[text=\dbaro@c] at (2.5*\dbarw+2*\dbarsep,-2.2mm) {\monofont\fontsize{6.8}{8}\selectfont HARD};
    \node[text=\dbaro@d] at (3.5*\dbarw+3*\dbarsep,-2.2mm) {\monofont\fontsize{6.8}{8}\selectfont INSANE};
  \end{tikzpicture}%
}
\newlength{\dbarsep}\setlength{\dbarsep}{1.8mm}

%% ------------------------------------------------------------- command pill
%% The one tactile affordance: a warm-filled, sharp-cornered chip that holds
%% a copyable command. A small prompt marker starts it. Reads as a unit the
%% player can reach for.
\newcommand{\cmdbox}[1]{%
  \begin{tcolorbox}[
    enhanced, breakable, colback=warm, colframe=warm, boxrule=0pt,
    arc=0pt, left=1.4mm, right=1.4mm, top=1.4mm, bottom=1.4mm,
    boxsep=0pt, sharp corners,
  ]%
    {\monofont\fontsize{9.5}{13}\selectfont\color{ember}\textbullet\ }\hspace{0.6mm}%
    {\monofont\fontsize{9.5}{13}\selectfont\color{ink}#1}%
  \end{tcolorbox}%
}

%% ------------------------------------------------------------------- code
%% Quiet warm-filled code card. Only type gestures; no frame, no drop.
\lstdefinestyle{labcode}{
  basicstyle=\monofont\fontsize{9}{13}\selectfont\color{ink},
  backgroundcolor=\color{warm},
  frame=none,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
  breaklines=true,
  breakatwhitespace=false,
  aboveskip=2.4mm, belowskip=2.4mm,
  framexleftmargin=3mm, framexrightmargin=3mm,
  framextopmargin=2mm, framexbottommargin=2mm,
  xleftmargin=0mm, xrightmargin=0mm,
}
\lstset{style=labcode}

%% Fenced inline code in body text.
\lstdefinestyle{labinline}{
  basicstyle=\monofont\fontsize{8.6}{13}\selectfont\color{ink},
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
}

\endinput