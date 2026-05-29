export const Link = ({
  href,
  children,
}: {
  href: string | undefined;
  children: React.ReactNode;
  checkLinkCredibility?: boolean;
}) => {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
};
