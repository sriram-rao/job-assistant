% Created by Murat Can Karacabey
% this is inspired by Michael Pollind's Awesome CV 
% Created from scratch as a much simpler alternative to it to actually learn LaTeX.
% Might be interpreted as an easier-to-edit or easier-to-understand-what-is-going-on version of it.
\author{Murat Can Karacabey}
\RequirePackage[dvipsnames]{xcolor} % moved here I guess article class causes option clash with xcolor if used after loading the class
\LoadClass[11pt]{article}
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{muratcan_cv}[2020/04/15 Muratcan CV Class]
\RequirePackage[sfdefault]{noto}
\RequirePackage{etoolbox}
\RequirePackage{pgffor}
\RequirePackage{titlesec}
\RequirePackage{tikz}
\RequirePackage{fontspec}
\RequirePackage[left=0.5in,top=0.1in,right=0.5in,bottom=0.1in]{geometry} % DOCUMENT MARGINS 
\RequirePackage{hyperref}
\RequirePackage{fontawesome}
\RequirePackage[inline]{enumitem}
\RequirePackage{mfirstuc}
\RequirePackage{ifthen}
\RequirePackage{lipsum}
\RequirePackage{setspace}
\RequirePackage{array}
\pagestyle{empty}

\usepackage{comment}

%Setup
\newcommand*{\setname}[2]{\def\@firstname{#1}\def\@lastname{#2}}
\newcommand*{\setaddress}[1]{\def\@address{#1}}
\newcommand*{\setmobile}[1]{\def\@mobile{#1}}
\newcommand*{\setposition}[1]{\def\@position{#1}}
\newcommand*{\setmail}[1]{\def\@mail{#1}}
\newcommand*{\setcitizenship}[1]{\def\@citizenship{#1}}
\newcommand*{\setthemecolor}[1]{\def\@themecolor{#1}}
\newcommand*{\setthemesubcolor}[1]{\def\@themesubcolor{#1}}
\newcommand*{\setlinkedinaccount}[1]{\def\@linkedinaccount{#1}}
\newcommand*{\setgithubaccount}[1]{\def\@githubaccount{#1}}

\hypersetup{
    colorlinks=true,
    urlcolor=NavyBlue, % URL COLOR!
}

\linespread{1.1}

% Header
\newcommand\headerview{
\hfill
\begin{minipage}{0.55\linewidth} % extend header length here
    \center \name \\[0.05cm] 
    \hspace{-3.5mm}
    \contact % address \ mobile \\ mail
\end{minipage}
\hfill
}
    
\newcommand{\linkedinview}{\href{https://\@linkedinaccount}{\faLinkedinSquare\ \footnotesize \@linkedinaccount}}
\newcommand{\githubview}{\href{https://\@githubaccount}{\faGithubSquare\ \footnotesize \@githubaccount }}

\newcommand{\name}{%
    {\LARGE \color{\@themecolor} \@firstname \ \textsc{\@lastname}}
}

\newcommand{\contact}{%
        % {\small \@address  \cps \@citizenship \\ \@mobile \cps \@mail% %%OLD
        {\small \@mail \ \cpshalf \@mobile %
        \\%
        \small \linkedinview \cpshalf \githubview \\ 
        } % 
}


% Helper commands
\newcommand\ruleafter[1]{#1~{\color{black!60!\@themecolor}\hrulefill}} % a trick to put the line with <before> parameter in \titleformat

%colorful pipe separator
\newcommand{\cps}{{\color{\@themecolor} \quad\textbar\quad}}
\newcommand{\cpshalf}{{\color{\@themecolor} \textbar\hspace{0.2em}}}
\newcommand{\coloredbullet}{{\color{\@themecolor} \textbullet}}

% Edit section styles
\titleformat{\section}      % Customise the \section command 
  {\large\bfseries\scshape\raggedright\color{\@themecolor}} % Make the \section headers large (\Large),
                               % small capitals (\scshape) and left aligned (\raggedright)
  {}{0em}                      % Can be used to give a prefix to all sections, like 'Section ...'
  {\ruleafter}                           % Can be used to insert code before the heading

\titlespacing*{\section}{-1pt}{1pt}{7.5pt}

\titleformat{\subsection}      % Customise the \section command 
  {\small\bfseries\scshape\raggedright\color{\@themesubcolor}} % Make the \section headers large (\Large),
                               % small capitals (\scshape) and left aligned (\raggedright)
  {}{1em}                      % Can be used to give a prefix to all sections, like 'Section ...' 
  {} 

\titlespacing*{\subsection}{-1pt}{1pt}{1pt}

% Textview commands
\newcommand{\experience}[2]{%
  \mbox { \hspace{1em} \scshape \textbf{#1} }%
}

\newcommand{\datetext}[1]{%
{\itshape  \small \mdseries \color{black} #1 } 
}

\newcommand{\datetextbold}[1]{%
{\small \mdseries \color{black} \textbf{#1} } 
}

\newcommand{\datedexperience}[2]{%
  {\color{\@themecolor} \begin{small} \mbox { \hspace{0.5em} \textbf{#1} } \end{small} \hfill \datetextbold{#2}\\[0cm]} %
}

\newcommand{\explanation}[2]{%
    \mbox { \hspace{0.5em} \small \color{\@themesubcolor} \emph{#1}} \hfill \datetext{#2}\\[0.05cm] %
}

\newcommand{\explanationdetail}[1]{%
    \hspace{0.9cm}\begin{minipage}{\linewidth} \fontsize{9.5}{11}\selectfont{#1}\vspace{1mm} \end{minipage} \\[0.15cm]
}

\newcommand\createskill[2]{%
    \textbf{#1} & #2
}

\newcommand\createskills[1]{%
\explanationdetail{
  \begin{tabular}{rl}
    \makeatletter
    \@for\thisitem:=#1\do{\thisitem\\[0cm]}
    \makeatother
  \end{tabular}
}
}
