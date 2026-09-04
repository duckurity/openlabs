export const Logo = (props: React.SVGProps<SVGSVGElement>) => {
  return (
    <svg
      width="40"
      height="40"
      viewBox="0 0 250 250"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...props}
    >
      <path d="M83.3334 166.666V250H166.666V166.666H83.3334Z" fill="currentColor" opacity="0.9" />
      <path d="M83.3334 0V83.3334H166.666V0H83.3334Z" fill="currentColor" opacity="0.9" />
      <path d="M166.666 166.666H250V83.3334H166.666V166.666Z" fill="currentColor" opacity="0.9" />
      <path d="M83.3334 83.3334H0V166.666H83.3334V83.3334Z" fill="currentColor" opacity="0.9" />
      <path d="M83.3334 0H0V83.3334H83.3334V0Z" fill="#FF3616" />
    </svg>
  )
}
