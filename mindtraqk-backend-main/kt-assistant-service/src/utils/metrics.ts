import * as appInsights from 'applicationinsights';

export const createMetricsClient = () => {
    if (!appInsights.defaultClient) {
        appInsights.setup(process.env.APPINSIGHTS_INSTRUMENTATIONKEY)
            .setAutoDependencyCorrelation(true)
            .setAutoCollectRequests(true)
            .setAutoCollectPerformance(true)
            .setAutoCollectExceptions(true)
            .setAutoCollectDependencies(true)
            .setAutoCollectConsole(true)
            .setUseDiskRetryCaching(true)
            .start();
    }
    return appInsights.defaultClient;
};