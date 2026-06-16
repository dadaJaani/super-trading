import { Module } from '@nestjs/common';
import { RedisModule } from '../redis/redis.module';
import { TradingGateway } from './trading/trading.gateway';

@Module({
  imports: [RedisModule],
  providers: [TradingGateway],
})
export class GatewayModule {}
