import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHouse,
  faWandMagicSparkles,
  faBell,
  faChartLine,
  faTerminal,
  faSearch,
  faChevronDown,
  faChevronRight,
  faSun,
  faMoon,
  faBars,
  faXmark,
  faList,
  faCopy,
  faCheck,
  faRocket,
  faScaleBalanced,
  faComments,
  faTriangleExclamation,
  faBookOpen,
  faCalendar,
  faShield,
  faBellSlash,
  faLayerGroup,
  faCircleQuestion,
  faUserGear,
  faFileLines,
  faLightbulb,
  faCircleInfo,
  faCircleExclamation,
  faArrowUpRightFromSquare,
} from "@fortawesome/free-solid-svg-icons";
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
  faHouse as houseOutline,
  faBell as bellOutline,
  faComments as commentsOutline,
  faSun as sunOutline,
  faMoon as moonOutline,
  faCopy as copyOutline,
  faLightbulb as lightbulbOutline,
  faCircleQuestion as questionOutline,
} from "@fortawesome/free-regular-svg-icons";
const icons: Record<string, IconDefinition> = {
  home: faHouse,
  sparkles: faWandMagicSparkles,
  bell: faBell,
  chart: faChartLine,
  terminal: faTerminal,
  search: faSearch,
  down: faChevronDown,
  right: faChevronRight,
  sun: faSun,
  moon: faMoon,
  menu: faBars,
  close: faXmark,
  list: faList,
  copy: faCopy,
  check: faCheck,
  rocket: faRocket,
  "scale-balanced": faScaleBalanced,
  comments: faComments,
  "triangle-exclamation": faTriangleExclamation,
  book: faBookOpen,
  calendar: faCalendar,
  shield: faShield,
  "bell-slash": faBellSlash,
  "layer-group": faLayerGroup,
  "circle-question": faCircleQuestion,
  "user-gear": faUserGear,
  "file-lines": faFileLines,
  tip: faLightbulb,
  info: faCircleInfo,
  warning: faCircleExclamation,
  external: faArrowUpRightFromSquare,
};
const outlines: Record<string, IconDefinition> = {
  home: houseOutline,
  bell: bellOutline,
  comments: commentsOutline,
  sun: sunOutline,
  moon: moonOutline,
  copy: copyOutline,
  tip: lightbulbOutline,
  "circle-question": questionOutline,
};
export function Icon({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  return (
    <FontAwesomeIcon
      icon={outlines[name] ?? icons[name] ?? faBookOpen}
      className={className}
      fixedWidth
    />
  );
}
