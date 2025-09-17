import { NavLink, useLocation, type To } from 'react-router-dom';

type Props = { to: To } & React.ComponentProps<typeof NavLink>;

export function PreserveSearchNavLink({ to, className, ...props }: Props) {
    const { search } = useLocation();
    const finalTo =
        typeof to === 'string'
            ? { pathname: to, search }
            : { ...to, search: to.search ?? search };

    const base =
        'underline data-[active=true]:font-semibold data-[active=true]:underline-offset-4';

    return (
        <NavLink
            to={finalTo}
            className={({ isActive }) =>
                [base, typeof className === 'function' ? className({ isActive, isPending: false, isTransitioning: false }) : className]
                    .filter(Boolean)
                    .join(' ')
            }
            // on fournit aussi un data-attr pratique pour le style (pas obligatoire)
            end
            {...props}
        />
    );
}
