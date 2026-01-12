import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import styles from './MarkdownComponents.module.css';

export const markdownComponents = {
  code({ inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '');
    return !inline && match ? (
      <SyntaxHighlighter
        style={oneDark}
        language={match[1]}
        PreTag="div"
        className={styles.codeBlock}
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code className={styles.inlineCode} {...props}>
        {children}
      </code>
    );
  },
  p: ({ children }: any) => <p className={styles.paragraph}>{children}</p>,
  ul: ({ children }: any) => <ul className={styles.list}>{children}</ul>,
  ol: ({ children }: any) => <ol className={styles.orderedList}>{children}</ol>,
  li: ({ children }: any) => <li className={styles.listItem}>{children}</li>,
  blockquote: ({ children }: any) => (
    <blockquote className={styles.blockquote}>{children}</blockquote>
  ),
  h1: ({ children }: any) => <h1 className={styles.heading1}>{children}</h1>,
  h2: ({ children }: any) => <h2 className={styles.heading2}>{children}</h2>,
  h3: ({ children }: any) => <h3 className={styles.heading3}>{children}</h3>,
  a: ({ href, children }: any) => (
    <a href={href} className={styles.link} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  table: ({ children }: any) => (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>{children}</table>
    </div>
  ),
  thead: ({ children }: any) => <thead>{children}</thead>,
  tbody: ({ children }: any) => <tbody>{children}</tbody>,
  tr: ({ children }: any) => <tr>{children}</tr>,
  th: ({ children }: any) => <th>{children}</th>,
  td: ({ children }: any) => <td>{children}</td>,
};
